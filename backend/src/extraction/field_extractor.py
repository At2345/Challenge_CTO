"""Deterministic, label-based extraction of the eleven target invoice fields
from raw invoice text (German conventions).

This module is an MVP stand-in for the semantic extraction stage described
in the architecture report (which envisions a pseudonymized payload sent to
an external LLM). No external model is wired up yet, so extraction runs
locally via regex heuristics rather than an LLM call. The caller
(`main.py::_run_pipeline`) still routes text through
`security/anonymizer.sanitize()`/`reidentify()` before/after this function
runs, exercising the same pseudonymization seam an external call would use.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Pattern

from ..utils.numbers import parse_decimal

MANDATORY_FIELDS = [
    "invoice_number",
    "invoice_date",
    "net_amount",
    "vat_amount",
    "gross_amount",
    "currency",
]

_DATE_PATTERNS = ["%d.%m.%Y", "%Y-%m-%d", "%d.%m.%y"]


def _normalize_date(raw: str) -> Optional[str]:
    raw = raw.strip()
    for fmt in _DATE_PATTERNS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _search(patterns: List[Pattern], text: str) -> Optional[str]:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _compile_all(raw_patterns: List[str]) -> List[Pattern]:
    return [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in raw_patterns]


_RECIPIENT_LABEL_RE = re.compile(
    r"^(Rechnungsempf[aä]nger|Leistungsempf[aä]nger|Rechnung\s*an|Bill\s*To|Empf[aä]nger|An)\s*:?",
    re.IGNORECASE,
)

# Words that indicate a line/segment belongs to a *different* field (e.g. the
# neighboring column in a two-column header table), used to avoid
# cross-column contamination when the recipient label and an unrelated
# label (invoice number, dates, customer number, ...) end up on the same
# physical text line after PDF text extraction.
_OTHER_LABEL_HINTS_RE = re.compile(
    r"rechnungs(?:-)?nr|invoice\s*number|invoice\s*no|ausgestellt|f[aä]llig|kundennr|kundenkonto|"
    r"zahlbar\s*bis|leistungsdatum|leistungszeitraum|abrechnungszeitraum|rechnungsdatum|rechnung\s*:",
    re.IGNORECASE,
)

_LEGAL_FORM_RE = re.compile(r"\b(GmbH|mbH|AG|KG|UG|SE|KGaA)\b", re.IGNORECASE)

# Street-address fragment (e.g. "Kanzleiplatz 3", "Handwerkerstraße 18") that
# PDF text extraction may merge onto the same physical line as a letterhead
# company name when the address sits in a neighboring column of the same
# visual row (column widths/gaps are not reliably preserved in extracted
# text).
_STREET_ADDRESS_RE = re.compile(
    r"\b[A-ZÄÖÜ][\wäöüß.\-]*(?:stra(?:ss|ß)e|str\.|weg|platz|allee|ring|gasse)\s*\d+[a-zA-Z]?\b",
    re.IGNORECASE,
)

# Postal-code + city fragment (e.g. "66119 Saarbrücken") with the same
# column-merging risk as `_STREET_ADDRESS_RE` above.
_POSTAL_CITY_RE = re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][\wäöüß\-]*\b")


def _strip_address_fragments(line: str) -> str:
    """Remove a trailing street or postal-code/city fragment that a merged
    two-column PDF text extraction placed alongside a letterhead name on
    the same physical line (e.g. "JURISMUSTER Kanzleiplatz 3" or
    "BERATUNG GMBH 66119 Saarbrücken"), so the address text isn't mistaken
    for part of the company name.
    """
    for pattern in (_STREET_ADDRESS_RE, _POSTAL_CITY_RE):
        match = pattern.search(line)
        if match:
            line = line[: match.start()]
    return line.strip(" ,;:\t-")

# Matches a merged two-column header row like "Von An" / "VON AN" /
# "Lieferant Empfänger", produced when a vendor-side label and a
# recipient-side label sit in the same visual row and collapse onto one
# physical text line. Used to know where the vendor's own letterhead/
# branding block ends and the actual vendor/recipient data table begins,
# so branding lines mentioning the vendor's name aren't mistaken for the
# recipient by the legal-form fallback scan below.
_VENDOR_RECIPIENT_HEADER_RE = re.compile(
    r"\b(Von|Lieferant|Verk[aä]ufer)\b.*\b(An|Empf[aä]nger|Rechnungsempf[aä]nger)\b",
    re.IGNORECASE,
)

# Matches a bare "Rechnung <code>" / "Invoice <code>" header line (label
# plus a single alphanumeric token, no other real words) -- e.g. a
# document title like "Rechnung GW-2026-0188" printed near the top. This is
# distinct from prose like "Rechnung für Reparaturarbeiten" (multiple real
# words) and must not be mistaken for the vendor's name by the vendor_name
# fallback heuristic.
_INVOICE_HEADER_LINE_RE = re.compile(
    r"^(?:Rechnung|Invoice)\s+[A-Za-z0-9][A-Za-z0-9\-\/]*$",
    re.IGNORECASE,
)

# Matches an individual "<Company Name> <legal form>" entity span (e.g.
# "Glanzwerk Musterreinigung GmbH" or "SAIAS Immobilien SPV 01 GmbH"). The
# non-greedy inner repetition stops at the *nearest* legal-form suffix, so
# `finditer` over a line containing two adjacent entities (vendor and
# recipient columns merged onto one physical line with only a single space
# between them) yields each entity as a separate match instead of one match
# spanning both.
_ENTITY_RE = re.compile(
    r"[A-ZÄÖÜ][\wÄÖÜäöüß]*(?:[\s.&-]+[A-Za-z0-9ÄÖÜäöüß][\wÄÖÜäöüß]*)*?\s+(?:GmbH|mbH|AG|KG|UG|SE|KGaA)\b"
)

_BARE_DATE_RE = re.compile(r"\b([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b")

# Lines containing these keywords carry a *different* date (service date /
# payment due date / billing period), so the bare-date header fallback below
# must skip them to avoid misidentifying that date as the invoice date.
_NON_INVOICE_DATE_LINE_RE = re.compile(
    r"leistungsdatum|leistungszeitraum|abrechnungszeitraum|zahlbar|f[aä]llig",
    re.IGNORECASE,
)

# Table-header row continuations (e.g. "Beschreibung Menge Betrag") that a
# naive "Beschreibung:?\s*(.+)" match would otherwise mistake for an actual
# description value.
_TABLE_HEADER_ROW_RE = re.compile(
    r"^(?:Menge|Betrag|Preis|Anzahl|St(?:k|ück)|Summe|EUR|Datum)"
    r"(?:\s+(?:Menge|Betrag|Preis|Anzahl|St(?:k|ück)|Summe|EUR|Datum))*$",
    re.IGNORECASE,
)

# A line-item row ending in "<quantity> <amount> EUR|€" (e.g.
# "Unterhaltsreinigung Objekt - August 2026 1 500,00 EUR") -- used as a
# description fallback when no explicit "Beschreibung"/"Leistungsbeschreibung"
# label yields a real value (only a table header row was found instead).
_LINE_ITEM_RE = re.compile(r"^(.+?)\s+\d+\s+[\d.,]+\s*(?:€|EUR)\s*$", re.IGNORECASE)


def _strip_trailing_other_column(line: str) -> str:
    """Truncate a text line at the point where an unrelated field's label
    begins, isolating the left column's content.

    Extracted PDF text sometimes collapses a two-column header row (e.g.
    recipient block on the left, invoice number/date block on the right)
    onto a single physical line with only a single space between columns
    (whitespace width is not reliably preserved), so splitting on wide gaps
    is not sufficient. Instead, this truncates the line at the first
    occurrence of a known "other field" label, regardless of the
    surrounding whitespace.
    """
    match = _OTHER_LABEL_HINTS_RE.search(line)
    if match:
        return line[: match.start()].strip(" ,;:\t-")
    return line.strip()


def _extract_recipient(text: str, vendor_name: Optional[str] = None) -> Optional[str]:
    """Locate the invoice recipient robustly against two-column layouts and
    label-less documents.

    PDF text extractors (pdfplumber/PyMuPDF) emit text in reading order based
    on vertical position; when a document places the recipient block and an
    unrelated block (e.g. invoice number/date) side-by-side in the same
    visual row, both end up concatenated on a single physical text line. A
    naive `label:?\s*(.+)$` regex then risks capturing the neighboring
    column's label (or its value) instead of the actual recipient name.
    This function inspects the label line, truncates same-line trailing
    text at the start of another field's label, and falls back to the
    next non-empty line(s) with the same truncation applied.

    Some invoice templates omit an explicit "Rechnungsempfänger"/"Empfänger"
    label altogether -- the recipient's name/address simply appears as a
    block beneath the vendor's own letterhead. When no label match is
    found, fall back to scanning for the first line containing a legal-form
    suffix (GmbH, AG, KG, ...) that is distinct from the already-identified
    vendor name, since the recipient's company name is the next such entity
    mentioned in the document.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        match = _RECIPIENT_LABEL_RE.match(line.strip())
        if not match:
            continue
        remainder = line.strip()[match.end():].strip(" :\t")
        remainder = _strip_trailing_other_column(remainder) if remainder else remainder
        if remainder:
            return remainder
        for j in range(i + 1, min(i + 3, len(lines))):
            raw_candidate = lines[j].strip()
            if not raw_candidate:
                continue
            candidate = _strip_trailing_other_column(raw_candidate)
            if candidate:
                return candidate

    scan_start = 0
    header_found = False
    for i, line in enumerate(lines):
        if _VENDOR_RECIPIENT_HEADER_RE.search(line):
            # Everything before a "Von ... An ..." style header is letterhead/
            # branding (may itself mention the vendor's name/legal form) and
            # must not be scanned for the recipient.
            scan_start = i + 1
            header_found = True
            break

    for line in lines[scan_start:]:
        stripped = line.strip()
        if header_found:
            # In a confirmed "Von ... An ..." layout, the vendor (left) and
            # recipient (right) entities are on the same data row, merged
            # onto one physical line. Split on individual entity spans
            # rather than relying on `vendor_name` (which may itself be
            # mis-extracted from letterhead noise) -- the last entity on
            # the row is the recipient by column order.
            entities = [m.group(0) for m in _ENTITY_RE.finditer(stripped)]
            if len(entities) >= 2:
                return entities[-1].strip()
        candidate = _strip_trailing_other_column(stripped)
        if not candidate or not _LEGAL_FORM_RE.search(candidate):
            continue
        if vendor_name and candidate == vendor_name:
            continue
        if vendor_name and vendor_name in candidate:
            # Merged two-column row containing both the vendor's own name and
            # the recipient's (e.g. "Vendor GmbH Recipient GmbH"); isolate the
            # text following the vendor's name.
            remainder = candidate[candidate.index(vendor_name) + len(vendor_name):].strip(" ,;:\t-")
            if remainder and _LEGAL_FORM_RE.search(remainder):
                return remainder
            continue
        if vendor_name and candidate in vendor_name:
            continue
        return candidate
    return None


def _extract_vendor_from_von_an_header(text: str) -> Optional[str]:
    """Counterpart to the "Von ... An ..." handling in `_extract_recipient`:
    when that merged two-column header is present, the first entity on the
    following data row (left column) is the vendor.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if _VENDOR_RECIPIENT_HEADER_RE.search(line):
            for candidate_line in lines[i + 1 : i + 4]:
                entities = [m.group(0) for m in _ENTITY_RE.finditer(candidate_line.strip())]
                if len(entities) >= 2:
                    return entities[0].strip()
            break
    return None


def _extract_vendor_from_letterhead(text: str) -> Optional[str]:
    """Fallback vendor-name heuristic for documents with neither an explicit
    "Lieferant:"/"Von:" label nor a merged "Von ... An ..." two-column
    header (e.g. a plain letterhead block at the top of the page).

    Rather than naively taking the *first* non-trivial header line (which
    misfires when a neighboring address column has been merged onto that
    same physical line by PDF text extraction, e.g. "JURISMUSTER
    Kanzleiplatz 3"), this scans the letterhead area specifically for a
    line carrying a legal-form suffix (GmbH, AG, ...) -- the actual
    signal that a line names a company -- after stripping any merged
    address fragment. Some letterheads additionally split the company
    name across two lines by font size (e.g. "JURISMUSTER" in a large
    logo font, "BERATUNG GMBH" underneath in a smaller font); when the
    legal-form line alone looks like a truncated continuation (a short,
    non-address, non-legal-form line immediately precedes it), that
    preceding line is prefixed onto it.

    Scanning stops at the first recipient label or other unrelated field
    label, since content beyond that point is no longer part of the
    vendor's own letterhead.
    """
    lines = text.splitlines()
    prev_candidate: Optional[str] = None
    for line in lines:
        stripped_raw = line.strip()
        if _RECIPIENT_LABEL_RE.match(stripped_raw) or _OTHER_LABEL_HINTS_RE.search(stripped_raw):
            break
        stripped = _strip_address_fragments(stripped_raw)
        if not stripped:
            prev_candidate = None
            continue
        if _LEGAL_FORM_RE.search(stripped):
            if (
                prev_candidate
                and not _LEGAL_FORM_RE.search(prev_candidate)
                and len(prev_candidate.split()) <= 3
            ):
                return f"{prev_candidate} {stripped}".strip()
            return stripped
        prev_candidate = stripped
    return None


def _extract_bare_header_date(text: str) -> Optional[str]:
    """Fallback for templates that print the invoice date as a bare,
    unlabeled date near the top of the document (e.g. merged onto a
    letterhead tagline line: "Musterreinigung GmbH 03.09.2026"), with no
    "Rechnungsdatum"/"Datum" label at all.

    Restricted to the header area (before any "Von ... An ..." vendor/
    recipient table, if present) and skips lines carrying an unrelated date
    (service date, due date, billing period) to avoid misattribution.
    """
    lines = text.splitlines()
    header_end = len(lines)
    for i, line in enumerate(lines):
        if _VENDOR_RECIPIENT_HEADER_RE.search(line):
            header_end = i
            break
    for line in lines[:header_end]:
        if _NON_INVOICE_DATE_LINE_RE.search(line):
            continue
        match = _BARE_DATE_RE.search(line)
        if match:
            return match.group(1)
    return None


def _extract_description(text: str) -> Optional[str]:
    """Locate the service/line-item description, guarding against a naive
    label match capturing a table header row (e.g. "Beschreibung Menge
    Betrag" from a "Beschreibung | Menge | Betrag" column header) instead of
    an actual description value.
    """
    for pattern in _PATTERNS["description"]:
        match = pattern.search(text)
        if match:
            candidate = match.group(1).strip()
            if candidate and not _TABLE_HEADER_ROW_RE.match(candidate):
                return candidate

    for line in text.splitlines():
        match = _LINE_ITEM_RE.match(line.strip())
        if match:
            candidate = match.group(1).strip(" -·\t")
            if candidate:
                return candidate
    return None


_PATTERNS = {
    "vendor_name": _compile_all(
        [
            r"^Rechnungssteller\s*:\s*(.+)$",
            r"^Lieferant\s*:\s*(.+)$",
            r"^Verk[aä]ufer\s*:\s*(.+)$",
            r"^Von\s*:\s*(.+)$",
        ]
    ),
    "invoice_number": _compile_all(
        [
            r"Rechnungs(?:-)?Nr\.?:?\s*([A-Za-z0-9\-\/]+)",
            r"Rechnungsnummer:?\s*([A-Za-z0-9\-\/]+)",
            r"Invoice\s*Number:?\s*([A-Za-z0-9\-\/]+)",
            r"^Rechnung\s*:\s*([A-Za-z0-9\-\/]+)",
            # Bare "Rechnung <code>" title line with no colon (e.g. a document
            # title "Rechnung GW-2026-0188"), distinct from prose like
            # "Rechnung für Reparaturarbeiten" since the value must be a single
            # alphanumeric/dash token.
            r"^Rechnung\s+([A-Za-z0-9][A-Za-z0-9\-\/]*)$",
        ]
    ),
    "invoice_date": _compile_all(
        [
            r"Rechnungsdatum:?\s*([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
            # Negative lookbehind excludes compound labels like
            # "Leistungsdatum"/"Abrechnungsdatum" where "Datum" is a suffix,
            # not a standalone word.
            r"(?<![A-Za-zÄÖÜäöüß])Datum:?\s*([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
        ]
    ),
    "service_date": _compile_all(
        [
            r"Leistungsdatum:?\s*([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
            r"Leistungszeitraum:?\s*.*?([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
            # Fallback: some templates only give a single, generically-labeled
            # "Datum:" (as opposed to "Rechnungsdatum"/"Abrechnungsdatum") with
            # no separate Leistungsdatum -- treat it as doubling for the
            # service date. The negative lookbehind excludes compound labels
            # like "Rechnungsdatum"/"Ausstellungsdatum" where "Datum" is a
            # suffix, not a standalone word.
            r"(?<![A-Za-zÄÖÜäöüß])Datum:?\s*([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})",
        ]
    ),
    "currency": _compile_all([r"\b(EUR|€)\b"]),
    "net_amount": _compile_all(
        [
            r"Nettobetrag:?\s*([\d.,]+)",
            r"Netto(?:summe)?:?\s*([\d.,]+)",
            r"Zwischensumme:?\s*([\d.,]+)",
        ]
    ),
    "vat_rate": _compile_all(
        [
            r"(?:USt\.?-?Satz|MwSt\.?-?Satz|Steuersatz):?\s*([\d.,]+)\s*%",
            r"([\d.,]+)\s*%\s*(?:USt|MwSt|Umsatzsteuer)",
        ]
    ),
    "vat_amount": _compile_all(
        [
            # Prefer currency-suffixed amounts on the same line
            r"(?:USt\.?-?Betrag|MwSt\.?-?Betrag|Umsatzsteuer)[^\n]*?([\d\.,]+)\s*(?:€|EUR)\b",
            # Or forms like 'Umsatzsteuer (19%) 190,00'
            r"(?:USt\.?|MwSt\.?|Umsatzsteuer)\s*\(\s*[\d\.,]+\s*%\s*\)[^\n]*?([\d\.,]+)",
            # Fallback but ignore if the captured number is a percent (e.g., 19%)
            r"(?:USt\.?-?Betrag|MwSt\.?-?Betrag|Umsatzsteuer):?\s*([\d\.,]+)(?!\s*%)",
            # Bare label after the percentage, e.g. "19 % USt. 95,00 EUR"
            r"[\d.,]+\s*%\s*(?:USt\.?|MwSt\.?|Umsatzsteuer)\s*([\d.,]+)\s*(?:€|EUR)?",
        ]
    ),
    "gross_amount": _compile_all(
        [
            r"(?:Gesamtbetrag|Bruttobetrag|Rechnungsbetrag|Endbetrag):?\s*([\d.,]+)",
            # Bare "Gesamt" label without the "-betrag" suffix
            r"\bGesamt\b:?\s*([\d.,]+)",
        ]
    ),
    "description": _compile_all(
        [
            r"Leistungsbeschreibung:?\s*(.+)",
            r"Beschreibung:?\s*(.+)",
            r"Betreff:?\s*(.+)",
        ]
    ),
}


def extract_fields(text: str) -> Dict[str, Any]:
    """Extract the eleven target fields from raw invoice text.

    Returns a dict with string/float values. Missing fields are set to None.
    Amounts are rounded to 2 decimals via Decimal for precision safety.
    """
    result: Dict[str, Any] = {}

    for field in [
        "vendor_name",
        "invoice_number",
    ]:
        result[field] = _search(_PATTERNS[field], text)
    result["description"] = _extract_description(text)

    if not result.get("vendor_name"):
        result["vendor_name"] = _extract_vendor_from_von_an_header(text)

    if not result.get("vendor_name"):
        result["vendor_name"] = _extract_vendor_from_letterhead(text)

    if not result.get("vendor_name"):
        for line in text.splitlines():
            candidate = line.strip()
            # Skip obvious non-vendor lines or logo shouts: very short tokens, single all-caps word,
            # or generic headers. Prefer lines with spaces or legal-form suffixes.
            if not candidate:
                continue
            caps = candidate.isupper()
            single_word = len(candidate.split()) == 1
            looks_generic = candidate.lower() in {"rechnung", "invoice"}
            is_invoice_header_line = bool(_INVOICE_HEADER_LINE_RE.match(candidate))
            has_legal_form = bool(_LEGAL_FORM_RE.search(candidate))
            if (
                (len(candidate) < 8 and single_word)
                or looks_generic
                or is_invoice_header_line
                or (caps and single_word and not has_legal_form)
            ):
                continue
            result["vendor_name"] = candidate
            break

    result["invoice_recipient"] = _extract_recipient(text, result.get("vendor_name"))

    invoice_date_raw = _search(_PATTERNS["invoice_date"], text) or _extract_bare_header_date(text)
    result["invoice_date"] = _normalize_date(invoice_date_raw) if invoice_date_raw else None

    service_date_raw = _search(_PATTERNS["service_date"], text)
    result["service_date"] = _normalize_date(service_date_raw) if service_date_raw else None

    currency_raw = _search(_PATTERNS["currency"], text)
    result["currency"] = "EUR" if currency_raw in ("EUR", "€") else currency_raw

    for field in ["net_amount", "vat_amount", "gross_amount"]:
        raw = _search(_PATTERNS[field], text)
        if raw is not None:
            try:
                result[field] = float(parse_decimal(raw).quantize(parse_decimal("0.01")))
            except Exception:
                result[field] = None
        else:
            result[field] = None

    vat_rate_raw = _search(_PATTERNS["vat_rate"], text)
    if vat_rate_raw is not None:
        try:
            result["vat_rate"] = float(parse_decimal(vat_rate_raw))
        except Exception:
            result["vat_rate"] = None
    else:
        result["vat_rate"] = None

    # Fallback: if vat_rate is missing but net and VAT amounts are present, infer rate.
    if result.get("vat_rate") is None and result.get("net_amount") and result.get("vat_amount"):
        try:
            inferred = parse_decimal(str(result["vat_amount"])) * parse_decimal("100") / parse_decimal(
                str(result["net_amount"]) 
            )
            # Round to one decimal place to match common display (e.g., 19.0, 7.0)
            result["vat_rate"] = float(inferred.quantize(parse_decimal("0.1")))
        except Exception:
            pass

    return result
