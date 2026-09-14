"""Optional hosted open-weight LLM semantic field extraction.

Open-source alternative to routing invoice text through a closed-source
model (e.g. Anthropic Claude) for the "external model" extraction step
referenced in docs/development-plan.md ("Neuro-symbolic hybrid: OCR/vision +
semantic extraction" / "optional external model calls under DPA,
zero-retention"). This module talks to any OpenAI-compatible
chat-completions endpoint (Together.ai, Groq, Fireworks, ...) serving an
open-weight model (Llama 3.x, Qwen2.5, DeepSeek-V3, ...) instead, so no
invoice data is sent to a closed-source vendor.

Privacy: this function must only ever be called with already-pseudonymized
text (see security/anonymizer.py::sanitize) -- PII has been swapped for
surrogate `<ENTITY_TYPE_INDEX>` tokens by the caller before this module
runs, so no raw personal data leaves the process boundary.

Resilience: disabled by default (no API key configured). Whenever the
LLM call fails, times out, or returns a response that can't be parsed into
the expected shape, this module returns None so the caller
(main.py::_run_pipeline) falls back to the deterministic regex extractor
(field_extractor.py) -- the system keeps working fully offline/for free.
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from .. import config
from ..utils.numbers import parse_decimal

logger = logging.getLogger("invoice_booking.llm_extractor")

FIELDS = [
    "invoice_recipient",
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "service_date",
    "currency",
    "net_amount",
    "vat_rate",
    "vat_amount",
    "gross_amount",
    "description",
]

_AMOUNT_FIELDS = {"net_amount", "vat_rate", "vat_amount", "gross_amount"}
_DATE_FIELDS = {"invoice_date", "service_date"}

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)

_SYSTEM_PROMPT = (
    "You are a precise invoice data extraction assistant for German business "
    "invoices. Extract exactly the requested fields as strict JSON. If a "
    "field is not present in the text, use null -- never guess or invent a "
    "value. Dates must be normalized to ISO 8601 (YYYY-MM-DD). Amounts must "
    "be plain numbers (no currency symbols, no thousands separators, decimal "
    "point not comma). Respond with ONLY a JSON object, no prose, no "
    "markdown code fences."
)


def _build_user_prompt(text: str) -> str:
    field_list = ", ".join(FIELDS)
    return (
        f"Extract these fields from the invoice text below: {field_list}.\n\n"
        "Some entities in the text may already be pseudonymized as "
        "<ENTITY_TYPE_N> tokens (e.g. <VAT_ID_1>, <IBAN_1>) -- if such a "
        "token appears where a value belongs, return the token verbatim.\n\n"
        f"Invoice text:\n---\n{text}\n---\n\n"
        f"Respond with a single JSON object with exactly these keys: {field_list}."
    )


def is_enabled() -> bool:
    return bool(config.LLM_API_KEY)


def _coerce_amount(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(parse_decimal(value))
    except Exception:
        return None


def _coerce_date(value: Any) -> Optional[str]:
    if isinstance(value, str) and _ISO_DATE_RE.match(value.strip()):
        return value.strip()
    return None


def _coerce_str(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _parse_json_response(raw: str) -> Optional[Dict[str, Any]]:
    cleaned = _CODE_FENCE_RE.sub("", raw.strip()).strip()
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def extract_fields_llm(text: str) -> Optional[Dict[str, Any]]:
    """Call the configured hosted open-weight LLM to extract invoice fields.

    Never raises. Returns None if the LLM is not configured (no API key),
    the request fails (network/timeout/HTTP error), or the response isn't
    valid/parseable JSON -- callers must fall back to the deterministic
    regex extractor (field_extractor.extract_fields) in that case.
    """
    if not is_enabled():
        return None

    try:
        from openai import OpenAI

        client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL)
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(text)},
            ],
        )
        raw = response.choices[0].message.content
    except Exception:
        logger.exception("LLM extraction request failed; falling back to regex extractor.")
        return None

    parsed = _parse_json_response(raw or "")
    if parsed is None:
        logger.warning("LLM response was not valid JSON; falling back to regex extractor.")
        return None

    result: Dict[str, Any] = {}
    for field in FIELDS:
        raw_value = parsed.get(field)
        if field in _AMOUNT_FIELDS:
            result[field] = _coerce_amount(raw_value)
        elif field in _DATE_FIELDS:
            result[field] = _coerce_date(raw_value)
        else:
            result[field] = _coerce_str(raw_value)
    return result
