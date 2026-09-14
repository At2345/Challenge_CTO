"""Reversible PII pseudonymization for invoice text.

Stage 1 of the two-stage pipeline described in the architecture report:
deterministic pattern matching (regex + checksum) for structured financial
identifiers (German VAT IDs, IBANs, emails, phone numbers). Detected values
are replaced with surrogate tokens (<ENTITY_TYPE_INDEX>) so the grammatical
structure of the text is preserved for downstream semantic processing.

The mapping of token -> original value is returned to the caller and must
only be retained in volatile process memory (see security/memory_vault.py).
It must never be written to disk or transmitted externally.
"""
import re
from typing import Dict, Tuple

DE_VAT_RE = re.compile(r"\bDE[0-9]{9}\b")
IBAN_RE = re.compile(r"\b[A-Z]{2}[0-9]{2}[A-Z0-9]{10,30}\b")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+49|0)[\d\s/()-]{6,}\d\b")


def validate_de_vat_checksum(vat_id: str) -> bool:
    """Validate a German USt-IdNr using the official ISO 7064 MOD 11-10 style
    checksum algorithm used by the Bundeszentralamt für Steuern."""
    if not DE_VAT_RE.fullmatch(vat_id):
        return False
    digits = vat_id[2:]
    product = 10
    for digit in digits[:-1]:
        d = int(digit)
        s = (d + product) % 10
        if s == 0:
            s = 10
        product = (2 * s) % 11
    check_digit = (11 - product) % 10
    return check_digit == int(digits[-1])


def validate_iban_checksum(iban: str) -> bool:
    """Validate an IBAN using the ISO 13616 / ISO 7064 MOD 97-10 algorithm."""
    iban = iban.replace(" ", "").upper()
    if not IBAN_RE.fullmatch(iban):
        return False
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(ch, 36)) for ch in rearranged)
    try:
        return int(numeric) % 97 == 1
    except ValueError:
        return False


def sanitize(text: str) -> Tuple[str, Dict[str, str]]:
    """Detect sensitive entities in `text` and replace them with surrogate
    tokens. Returns (sanitized_text, mapping) where mapping is
    token -> original_value. The mapping must stay in memory only."""
    mapping: Dict[str, str] = {}
    counters: Dict[str, int] = {}

    def _replace(pattern: re.Pattern, entity_type: str, validator=None):
        nonlocal text

        def _sub(match: re.Match) -> str:
            value = match.group(0)
            if validator is not None and not validator(value):
                return value
            counters[entity_type] = counters.get(entity_type, 0) + 1
            token = f"<{entity_type}_{counters[entity_type]}>"
            mapping[token] = value
            return token

        text = pattern.sub(_sub, text)

    _replace(DE_VAT_RE, "VAT_ID", validate_de_vat_checksum)
    _replace(IBAN_RE, "IBAN", validate_iban_checksum)
    _replace(EMAIL_RE, "EMAIL")
    _replace(PHONE_RE, "PHONE")

    return text, mapping


def reidentify(text: str, mapping: Dict[str, str]) -> str:
    """Restore original values in `text` using the token -> original mapping."""
    for token, original in mapping.items():
        text = text.replace(token, original)
    return text
