from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import logging
import os
import uuid

from pymongo import ReturnDocument

from . import config
from .database import get_collection, serialize_document, log_audit_event
from . import master_data as fallback_master_data
from .extraction.pdf_loader import extract_text_with_method
from .extraction.field_extractor import extract_fields
from .extraction.llm_extractor import extract_fields_llm, is_enabled as llm_extraction_enabled
from .rules.engine import evaluate_invoice
from .accounting.proposal_builder import build_booking_proposal
from .security.anonymizer import sanitize, reidentify
from .models.invoice import InvoiceRecord, RevalidateRequest

logger = logging.getLogger("invoice_booking")

app = FastAPI(title="Invoice Booking System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory fallback store used only when MongoDB is unreachable (dev convenience).
invoices_mem: Dict[str, Dict[str, Any]] = {}


async def _load_master_data() -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    clients: List[Dict[str, Any]] = []
    creditors: List[Dict[str, Any]] = []
    clients_col = get_collection("clients")
    creditors_col = get_collection("creditors")
    try:
        if clients_col is not None:
            clients = await clients_col.find({}).to_list(length=100)
        if creditors_col is not None:
            creditors = await creditors_col.find({}).to_list(length=100)
    except Exception:
        clients = []
        creditors = []
    if not clients:
        clients = fallback_master_data.CLIENTS
    if not creditors:
        creditors = fallback_master_data.CREDITORS
    return clients[0], creditors


def _run_pipeline(pdf_path: str, client: Dict[str, Any], creditors: List[Dict[str, Any]]) -> Dict[str, Any]:
    text, extraction_method = extract_text_with_method(pdf_path)
    # Sanitize before any semantic extraction step (regex-based here; this is
    # the same seam an external LLM call would plug into). VAT IDs, IBANs,
    # emails, and phone numbers are swapped for surrogate tokens so no raw
    # PII is present during extraction; re-identify afterwards for the
    # deterministic rules engine and downstream master-data matching.
    sanitized_text, pii_mapping = sanitize(text)

    extraction_source = "regex_heuristics"
    extracted_sanitized = None
    if llm_extraction_enabled():
        extracted_sanitized = extract_fields_llm(sanitized_text)
        if extracted_sanitized is not None:
            extraction_source = f"llm:{config.LLM_MODEL}"
    if extracted_sanitized is None:
        extracted_sanitized = extract_fields(sanitized_text)

    extracted = {
        key: (reidentify(value, pii_mapping) if isinstance(value, str) else value)
        for key, value in extracted_sanitized.items()
    }
    evaluation = evaluate_invoice(extracted, client, creditors)

    booking_proposal: List[Dict[str, Any]] = []
    suggested = evaluation.get("suggested_expense_account")
    if not evaluation["blocked"] and suggested is not None and all(
        extracted.get(f) is not None for f in ("net_amount", "vat_amount", "vat_rate", "gross_amount")
    ):
        booking_proposal = build_booking_proposal(
            extracted["net_amount"],
            extracted["vat_amount"],
            extracted["vat_rate"],
            extracted["gross_amount"],
            suggested["account"],
        )

    return {
        "extracted": extracted,
        "validations": evaluation["validations"],
        "suggested_expense_account": suggested,
        "traffic_light": evaluation["traffic_light"],
        "decision_reasons": evaluation["decision_reasons"],
        "booking_proposal": booking_proposal,
        "blocked": evaluation["blocked"],
        "extraction_method": extraction_method,
        "extraction_source": extraction_source,
    }


def _new_invoice_document(invoice_id: str, filename: str, original_filename: str, pipeline_result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "_id": invoice_id,
        "invoice_file": filename,
        "original_filename": original_filename,
        "extracted": pipeline_result["extracted"],
        "validations": pipeline_result["validations"],
        "suggested_expense_account": pipeline_result["suggested_expense_account"],
        "traffic_light": pipeline_result["traffic_light"],
        "decision_reasons": pipeline_result["decision_reasons"],
        "booking_proposal": pipeline_result["booking_proposal"],
        "blocked": pipeline_result["blocked"],
        "audit": {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "model_or_method": (
                f"MultiEngineExtractor(pdfplumber+pymupdf+ocr, selected={pipeline_result['extraction_method']})"
                f"+FieldExtractor({pipeline_result['extraction_source']})+DeterministicRulesEngine_v1.0"
            ),
            "notes": "Direct through-the-wall processing. No manual interaction required."
            if not pipeline_result["blocked"]
            else "Workflow halted automatically. Human intervention mandatory to review invoice.",
        },
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/invoices/upload", response_model=InvoiceRecord)
async def upload_invoice(file: UploadFile = File(...)) -> Dict[str, Any]:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    invoice_id = str(uuid.uuid4())
    filename = f"{invoice_id}.pdf"
    dest_path = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    client, creditors = await _load_master_data()
    pipeline_result = _run_pipeline(dest_path, client, creditors)
    document = _new_invoice_document(invoice_id, filename, file.filename, pipeline_result)
    collection = get_collection("invoices")
    if collection is not None:
        try:
            await collection.insert_one(dict(document))
            await log_audit_event(invoice_id, "upload", {"filename": file.filename})
            return serialize_document(document)
        except Exception:
            logger.exception("Failed to persist invoice %s to MongoDB; falling back to in-memory store.", invoice_id)

    record = serialize_document(document)
    invoices_mem[invoice_id] = record
    return record


@app.get("/api/invoices", response_model=List[InvoiceRecord])
async def list_invoices() -> List[Dict[str, Any]]:
    collection = get_collection("invoices")
    if collection is not None:
        try:
            docs = await collection.find({}).to_list(length=1000)
            return [serialize_document(d) for d in docs]
        except Exception:
            pass
    return list(invoices_mem.values())


@app.get("/api/invoices/{invoice_id}", response_model=InvoiceRecord)
async def get_invoice(invoice_id: str) -> Dict[str, Any]:
    collection = get_collection("invoices")
    if collection is not None:
        try:
            doc = await collection.find_one({"_id": invoice_id})
            if doc is not None:
                return serialize_document(doc)
        except Exception:
            pass
    if invoice_id not in invoices_mem:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoices_mem[invoice_id]


@app.get("/api/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: str):
    pdf_name = None
    collection = get_collection("invoices")
    if collection is not None:
        try:
            doc = await collection.find_one({"_id": invoice_id})
            if doc is not None:
                pdf_name = doc["invoice_file"]
        except Exception:
            pass
    if pdf_name is None:
        if invoice_id not in invoices_mem:
            raise HTTPException(status_code=404, detail="Invoice not found")
        pdf_name = invoices_mem[invoice_id]["invoice_file"]
        orig_name = invoices_mem[invoice_id].get("original_filename", pdf_name)
    else:
        # load original filename from db if present
        try:
            collection = get_collection("invoices")
            if collection is not None:
                doc = await collection.find_one({"_id": invoice_id})
                if doc is not None:
                    orig_name = doc.get("original_filename", pdf_name)
                else:
                    orig_name = pdf_name
            else:
                orig_name = pdf_name
        except Exception:
            orig_name = pdf_name

    path = os.path.join(UPLOAD_DIR, pdf_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF not found")
    # Set content disposition to help user agents present the correct filename
    return FileResponse(path, media_type="application/pdf", filename=orig_name)


@app.post("/api/invoices/{invoice_id}/revalidate", response_model=InvoiceRecord)
async def revalidate_invoice(invoice_id: str, payload: RevalidateRequest) -> Dict[str, Any]:
    collection = get_collection("invoices")
    existing: Optional[Dict[str, Any]] = None
    if collection is not None:
        try:
            existing = await collection.find_one({"_id": invoice_id})
        except Exception:
            existing = None
    if existing is None:
        existing = invoices_mem.get(invoice_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Invoice not found")

    merged_extracted = dict(existing.get("extracted", {}))
    merged_extracted.update(payload.extracted)

    client, creditors = await _load_master_data()
    evaluation = evaluate_invoice(merged_extracted, client, creditors)

    booking_proposal: List[Dict[str, Any]] = []
    suggested = evaluation.get("suggested_expense_account")
    if not evaluation["blocked"] and suggested is not None and all(
        merged_extracted.get(f) is not None for f in ("net_amount", "vat_amount", "vat_rate", "gross_amount")
    ):
        booking_proposal = build_booking_proposal(
            merged_extracted["net_amount"],
            merged_extracted["vat_amount"],
            merged_extracted["vat_rate"],
            merged_extracted["gross_amount"],
            suggested["account"],
        )

    updates = {
        "extracted": merged_extracted,
        "validations": evaluation["validations"],
        "suggested_expense_account": suggested,
        "traffic_light": evaluation["traffic_light"],
        "decision_reasons": evaluation["decision_reasons"],
        "booking_proposal": booking_proposal,
        "blocked": evaluation["blocked"],
    }

    if collection is not None:
        try:
            result = await collection.find_one_and_update(
                {"_id": invoice_id},
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
            )
            if result is not None:
                await log_audit_event(invoice_id, "revalidate", updates)
                return serialize_document(result)
        except Exception:
            logger.exception("Failed to persist revalidation for invoice %s to MongoDB; falling back to in-memory store.", invoice_id)

    invoices_mem.setdefault(invoice_id, {"id": invoice_id})
    invoices_mem[invoice_id].update(updates)
    return invoices_mem[invoice_id]


@app.get("/api/master-data")
async def get_master_data() -> Dict[str, Any]:
    clients_col = get_collection("clients")
    creditors_col = get_collection("creditors")
    accounts_col = get_collection("accounts")
    if clients_col is None or creditors_col is None or accounts_col is None:
        raise HTTPException(status_code=503, detail="MongoDB is not reachable")
    try:
        clients = [serialize_document(d) for d in await clients_col.find({}).to_list(length=100)]
        creditors = [serialize_document(d) for d in await creditors_col.find({}).to_list(length=100)]
        accounts = [serialize_document(d) for d in await accounts_col.find({}).to_list(length=100)]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MongoDB query failed: {exc}")
    return {"clients": clients, "creditors": creditors, "accounts": accounts}
