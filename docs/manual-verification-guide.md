---
title: Manual Verification Guide
description: Step-by-step walkthrough to manually prove every feature of the Invoice Booking System against its code structures.
---

# Manual Verification Guide

This guide maps each feature of the app to the exact code that implements it, and gives you concrete manual steps (UI clicks, sample files, `curl` calls) to prove it works. Use it top-to-bottom, or jump to the section you need.

## 0. Environment Setup

**Start the stack:**
```
# Terminal 1 - MongoDB (or use existing local instance)
docker run -d -p 27017:27017 --name mongo-invoice mongo:7

# Terminal 2 - Backend
venv\Scripts\activate
python backend/data/seed_data.py
uvicorn src.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

# Terminal 3 - Frontend
cd frontend
npm run dev
```

**Regenerate sample invoices** (needed after any `field_extractor.py` change, or if `backend/data/sample_invoices/*.pdf` are missing):
```
venv\Scripts\python backend/data/sample_invoices/generate_samples.py
```

**Run the automated test suite** (fast sanity check before manual testing):
```
venv\Scripts\python -m pytest -q
```

- Frontend: http://localhost:5173
- Backend API docs (Swagger): http://localhost:8000/docs
- Master data check: http://localhost:8000/api/master-data

---

## 1. PDF Upload Pipeline

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\main.py:128-153` (`upload_invoice`), `@c:\Users\User\Challenge_CTO\Challenge_CTO\frontend\src\components\InvoiceSelector.tsx`

**Manual steps:**
1. In the browser, click **Upload** in the left sidebar (`InvoiceSelector`) and pick `backend/data/sample_invoices/invoice_01_energie_saar.pdf`.
2. Confirm a new entry appears in the list named `Rechnung-00001` (sequential naming, session-scoped — only invoices uploaded in this browser session show up).
3. Confirm it auto-selects and the PDF renders in the center pane.

**API-only proof:**
```
curl -F "file=@backend/data/sample_invoices/invoice_01_energie_saar.pdf" http://localhost:8000/api/invoices/upload
```
Expect HTTP 200 with a JSON body containing `id`, `extracted`, `traffic_light`.

---

## 2. Multi-Engine Text Extraction (pdfplumber + PyMuPDF + OCR arbitration)

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\extraction\pdf_loader.py` (`extract_text_with_method`, `_score_text`, `_HIGH_CONFIDENCE_SCORE`)

**Manual steps:**
1. Upload any sample invoice.
2. Open the invoice detail via `GET /api/invoices/{id}` (Swagger UI or `curl`) and inspect `audit.model_or_method`.
3. Confirm it reads like `MultiEngineExtractor(pdfplumber+pymupdf+ocr, selected=pdfplumber)...` — the `selected=` engine tells you which one won arbitration.
4. Since our samples are pure digital text (no scanned images), `pdfplumber` or `pymupdf` should always win and OCR should be skipped (high-confidence short-circuit).

**Automated proof:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\tests\test_pdf_loader.py` — run `pytest backend/tests/test_pdf_loader.py -v` and confirm `test_ocr_skipped_when_both_digital_engines_are_high_confidence` passes.

---

## 3. Field Extraction (11 target fields)

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\extraction\field_extractor.py` (`extract_fields`)

Fields: `invoice_recipient`, `vendor_name`, `invoice_number`, `invoice_date`, `service_date`, `currency`, `net_amount`, `vat_rate`, `vat_amount`, `gross_amount`, `description`.

**Manual steps (one per sample file — each exercises a different layout heuristic):**

| Sample file | Layout exercised | Expected `vendor_name` | Expected `invoice_recipient` |
|---|---|---|---|
| `invoice_01_energie_saar.pdf` | Standard labeled fields | `Beispiel Energie Saar GmbH` | `SAIAS Immobilien SPV 01 GmbH` |
| `invoice_05_immofix_no_label.pdf` | No `Rechnungsempfänger:` label; bare `Datum:` | `ImmoFix Musterservice GmbH` | `SAIAS Immobilien SPV 01 GmbH` |
| `invoice_06_glanzwerk_von_an.pdf` | Merged "VON AN" two-column header | `Glanzwerk Musterreinigung GmbH` | `SAIAS Immobilien SPV 01 GmbH` |
| `invoice_07_jurismuster_split_letterhead.pdf` | Company name split across 2 lines + merged address column, all-caps legal form | `JURISMUSTER BERATUNG GMBH` | `SAIAS Immobilien SPV 01 GmbH` |

For each: upload the file in the UI, check the **Extracted Invoice Data** panel (`ExtractedDataForm`) against the table above. All 11 fields should be populated (none blank) except where the layout genuinely omits a value.

**Automated proof:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\tests\test_field_extractor.py` and `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\tests\test_upload_pipeline_e2e.py` cover each layout with exact-value assertions.

---

## 4. PII Pseudonymization (GDPR seam)

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\security\anonymizer.py` (`sanitize`, `reidentify`, `validate_de_vat_checksum`, `validate_iban_checksum`)

**Manual steps:**
1. Upload `invoice_06_glanzwerk_von_an.pdf` (contains `IBAN DE86100100100056789012` and `USt-IdNr. DE777777773`).
2. Confirm the final extracted/displayed data still shows real values (re-identification happened correctly) — the pipeline sanitizes text *before* regex extraction and re-identifies *after*, per `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\main.py:61-73` (`_run_pipeline`).

**Automated proof:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\tests\test_anonymizer.py` — validates checksum logic and round-trip sanitize/reidentify.

---

## 5. Validation Rule Engine (R0–R8 Audit Trail)

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\rules\validators.py`, `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\rules\engine.py` (`evaluate_invoice`), UI: `@c:\Users\User\Challenge_CTO\Challenge_CTO\frontend\src\components\ValidationResults.tsx`

| Rule | Function | Severity | Trigger to test manually |
|---|---|---|---|
| R0 | `r0_overall_status` | meta | Any RED FAIL → overall RED; else any YELLOW WARN → YELLOW; else GREEN |
| R1 | `r1_recipient_match` | RED | Upload an invoice whose recipient text doesn't contain `SAIAS Immobilien SPV 01 GmbH` |
| R2 | `r2_mandatory_fields` | RED | Any of `invoice_number/invoice_date/net_amount/vat_amount/gross_amount/currency` missing |
| R3 | `r3_amount_balance` | RED | `invoice_03_invalid_calc.pdf` — Net+VAT ≠ Gross beyond 0.02 EUR tolerance |
| R4 | `r4_vat_plausibility` | RED | Edit `vat_rate` on a YELLOW invoice to a value inconsistent with `vat_amount` |
| R5 | `r5_service_date` | YELLOW (WARN) | `invoice_04_unknown_vendor.pdf` has no `Leistungsdatum` |
| R6 | `r6_creditor_master` | YELLOW (WARN) | `invoice_06_glanzwerk_von_an.pdf` — vendor `Glanzwerk Musterreinigung GmbH` is not seeded in `CREDITORS` (`@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\master_data.py:32-69`) |
| R7 | `r7_account_assignment` | YELLOW (WARN) | Vendor/description with no keyword match and no creditor match (none of the seeded samples trigger this — see note below) |
| R8 | `r8_happy_path` | meta | PASS only if overall status is GREEN |

**Manual steps:**
1. Upload `invoice_01_energie_saar.pdf` → expect **all-green** Audit Trail, `traffic_light: GREEN`, and a 3-line booking proposal auto-generated.
2. Upload `invoice_03_invalid_calc.pdf` → expect **R3 FAIL (RED)**, overall RED, `blocked: true`, empty booking proposal, and the "Automated processing blocked" banner.
3. Upload `invoice_04_unknown_vendor.pdf` → expect **R5 WARN** (no service date). Confirm overall status is YELLOW and the **Save & Revalidate** form becomes editable.
4. Upload `invoice_06_glanzwerk_von_an.pdf` → expect **R6 WARN** (vendor `Glanzwerk Musterreinigung GmbH` not in creditor master). R7 will still PASS here because the description contains "Reinigung", which resolves via the keyword heuristic (see Section 6).
5. To see **R7 WARN** manually, use **Save & Revalidate** (Section 8) on a YELLOW invoice to overwrite `vendor_name` with an unseeded name (e.g. `Unbekannt GmbH`) and `description` with something keyword-less (e.g. `Sonstige Leistungen`) — confirm the suggested account becomes empty and R7 flips to WARN.

**Automated proof:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\tests\test_engine_green_red.py`, `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\tests\test_arithmetic.py`.

---

## 6. Expense Account Suggestion (Kontierung)

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\rules\account_suggester.py` (`match_creditor`, `suggest_account`)

Three-tier fallback to prove:

1. **Creditor master match** — Upload `invoice_01_energie_saar.pdf` (`Beispiel Energie Saar GmbH` is seeded as creditor `K10001` with `default_expense_account: 4240`). Confirm suggested account = `4240 Energie / Nebenkosten`, `source: creditor_master`.
2. **Keyword heuristic fallback** — Upload `invoice_06_glanzwerk_von_an.pdf`. Its vendor `Glanzwerk Musterreinigung GmbH` is *not* in `CREDITORS`, but its description `"Unterhaltsreinigung Objekt - August 2026"` contains `"reinigung"`. Confirm suggested account = `4250 Reinigung`, `source: keyword_heuristic`.
3. **Unresolved** — Via **Save & Revalidate** (Section 8), overwrite `vendor_name`/`description` on a YELLOW invoice with values matching neither a creditor nor any `KEYWORD_RULES` term (e.g. `Unbekannt GmbH` / `Sonstige Leistungen`). Confirm `suggested_expense_account: null` and R7 WARN.

**Automated proof:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\tests\test_account_suggester.py`.

---

## 7. Booking Proposal Generation (Buchungssatz)

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\accounting\proposal_builder.py` (`build_booking_proposal`, `is_balanced`), UI: `@c:\Users\User\Challenge_CTO\Challenge_CTO\frontend\src\components\BookingProposalTable.tsx`

**Manual steps:**
1. Upload `invoice_01_energie_saar.pdf` (GREEN, net 1000/VAT 190/gross 1190 @ 19%).
2. In the **Booking Proposal** panel confirm 3 lines:
   - DEBIT `4240` (Energie/Nebenkosten) — 1000.00
   - DEBIT `1576` (Vorsteuer 19%) — 190.00
   - CREDIT `1600` (Verbindlichkeiten aus Lieferungen und Leistungen) — 1190.00
3. Confirm debit total (1190.00) == credit total (1190.00).
4. Upload `invoice_03_invalid_calc.pdf` (RED) → confirm booking proposal is **empty** (blocked invoices never get a proposal, per `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\main.py:76-87`).

**Automated proof:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\tests\test_booking.py`.

---

## 8. Manual Correction & Revalidation Workflow (YELLOW invoices)

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\main.py:221-279` (`revalidate_invoice`), UI: `@c:\Users\User\Challenge_CTO\Challenge_CTO\frontend\src\components\ExtractedDataForm.tsx`

**Manual steps:**
1. Upload `invoice_04_unknown_vendor.pdf` (YELLOW — missing service date).
2. Confirm the **Extracted Invoice Data** form fields are editable (only enabled when `traffic_light === "YELLOW"`, see `App.tsx:111`).
3. Fill in a `service_date` (e.g. `2026-03-01`) and click **Save & Revalidate**.
4. Confirm the Audit Trail refreshes, R5 flips to PASS, and (if no other WARN/FAIL remains) `traffic_light` becomes GREEN with a new booking proposal appearing.

**API-only proof:**
```
curl -X POST http://localhost:8000/api/invoices/{id}/revalidate \
  -H "Content-Type: application/json" \
  -d '{"extracted": {"service_date": "2026-03-01"}}'
```

---

## 9. PDF Preview & Original Filename Handling

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\frontend\src\components\PdfPreview.tsx`, `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\main.py:183-218` (`get_invoice_pdf`)

**Manual steps:**
1. Upload two different sample PDFs in sequence.
2. Switch between them in the sidebar and confirm the center pane always renders the **originally uploaded document** (not a stale/cached one) — verifies cache-busting query param and `Content-Disposition` filename logic.

---

## 10. Invoice List / Persistence

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\main.py:156-165` (`list_invoices`), `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\database.py`

**Manual steps:**
1. Upload a few invoices, then refresh the browser page (full reload).
2. Confirm the sidebar list is now empty (session-scoped filtering via `uploadedIds` in `App.tsx`, by design) — but confirm the records still exist server-side:
```
curl http://localhost:8000/api/invoices
```
3. Stop MongoDB and re-upload an invoice — confirm the app still works via the in-memory fallback store (`invoices_mem` in `main.py`), proving graceful degradation.

---

## 11. Master Data Endpoint

**Code:** `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\main.py:282-295`, `@c:\Users\User\Challenge_CTO\Challenge_CTO\backend\src\master_data.py`

**Manual steps:**
```
curl http://localhost:8000/api/master-data
```
Confirm it returns seeded `clients` (1 SPV), `creditors` (4 vendors: Energie Saar, ImmoFix, JurisMuster Beratung, OfficeMuster), and `accounts` (8 GL accounts) — matches `master_data.py`.

---

## Quick Reference: Full Automated Test Suite

Running this before/after manual testing gives you a fast regression baseline:
```
venv\Scripts\python -m pytest -v
```
| Test file | Feature covered |
|---|---|
| `test_health.py` | API liveness |
| `test_anonymizer.py` | PII sanitize/reidentify + checksums |
| `test_field_extractor.py` | Extraction heuristics per layout |
| `test_pdf_loader.py` | Multi-engine text extraction arbitration |
| `test_arithmetic.py` | R3/R4 arithmetic + VAT plausibility |
| `test_engine_green_red.py` | Full R0–R8 rule orchestration |
| `test_account_suggester.py` | Kontierung 3-tier fallback |
| `test_booking.py` | Booking proposal + balance check |
| `test_upload_pipeline_e2e.py` | Full upload → extract → validate → propose pipeline |
