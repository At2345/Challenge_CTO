from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from ..config import TOLERANCE_EUR
from ..utils.numbers import parse_decimal as _to_decimal
from .account_suggester import match_creditor

TOLERANCE = Decimal(TOLERANCE_EUR)

MANDATORY_FIELDS = [
    "invoice_number",
    "invoice_date",
    "net_amount",
    "vat_amount",
    "gross_amount",
    "currency",
]


def r3_amount_balance(net: Any, vat: Any, gross: Any, tolerance: Decimal = TOLERANCE) -> Dict[str, Any]:
    net_d = _to_decimal(net)
    vat_d = _to_decimal(vat)
    gross_d = _to_decimal(gross)
    delta = (net_d + vat_d) - gross_d
    passed = abs(delta) <= tolerance
    status = "PASS" if passed else "FAIL"
    details = (
        f"Net ({net_d:.2f}) + VAT ({vat_d:.2f}) equals Gross ({gross_d:.2f}). Discrepancy: {abs(delta):.2f} EUR."
        if passed
        else f"Arithmetic balance check failed: Net ({net_d:.2f}) + VAT ({vat_d:.2f}) = {(net_d+vat_d):.2f}, but Gross is {gross_d:.2f}. Delta of {abs(delta):.2f} EUR exceeds tolerance of {tolerance:.2f} EUR."
    )
    return {
        "check": "R3_Betragsprüfung",
        "severity": "RED",
        "status": status,
        "details": details,
        "delta": float(delta),
    }


def r4_vat_plausibility(net: Any, vat_rate: Any, vat_amount: Any, tolerance: Decimal = TOLERANCE) -> Dict[str, Any]:
    net_d = _to_decimal(net)
    rate_d = _to_decimal(vat_rate)
    vat_d = _to_decimal(vat_amount)
    expected = (net_d * rate_d / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    delta = expected - vat_d
    passed = abs(delta) <= tolerance
    status = "PASS" if passed else "FAIL"
    details = (
        f"VAT amount ({vat_d:.2f}) is consistent with {rate_d:.1f}% applied to net ({net_d:.2f})."
        if passed
        else f"VAT plausibility failed: expected {expected:.2f} from {rate_d:.1f}% of {net_d:.2f}, but got {vat_d:.2f}. Delta {abs(delta):.2f} EUR exceeds tolerance of {tolerance:.2f} EUR."
    )
    return {
        "check": "R4_USt_Plausibilität",
        "severity": "RED",
        "status": status,
        "details": details,
        "delta": float(delta),
    }


def r0_overall_status(validations: Tuple[Dict[str, Any], ...]) -> str:
    # Any RED with FAIL => RED; else any YELLOW with WARN => YELLOW; else GREEN
    for v in validations:
        if v.get("severity") == "RED" and v.get("status") == "FAIL":
            return "RED"
    for v in validations:
        if v.get("severity") == "YELLOW" and v.get("status") in {"WARN", "FAIL"}:
            return "YELLOW"
    return "GREEN"


def r1_recipient_match(invoice_recipient: Optional[str], client: Dict[str, Any]) -> Dict[str, Any]:
    expected = client.get("company_name", "")
    matched = bool(invoice_recipient) and expected.strip().lower() in invoice_recipient.strip().lower()
    status = "PASS" if matched else "FAIL"
    details = (
        f"Recipient corresponds to target SPV: {expected}."
        if matched
        else f"Extracted recipient ('{invoice_recipient}') does not match client master record ('{expected}')."
    )
    return {"check": "R1_Rechnungsempfänger", "severity": "RED", "status": status, "details": details}


def r2_mandatory_fields(extracted: Dict[str, Any]) -> Dict[str, Any]:
    missing = [f for f in MANDATORY_FIELDS if extracted.get(f) in (None, "")]
    status = "PASS" if not missing else "FAIL"
    details = (
        "All mandatory invoice fields are populated."
        if not missing
        else f"Missing mandatory field(s): {', '.join(missing)}."
    )
    return {"check": "R2_Pflichtfelder", "severity": "RED", "status": status, "details": details}


def r5_service_date(extracted: Dict[str, Any]) -> Dict[str, Any]:
    service_date = extracted.get("service_date")
    status = "PASS" if service_date else "WARN"
    details = (
        f"Service date identified: {service_date}."
        if service_date
        else "No service date (Leistungsdatum) could be identified. Clerk review required per § 14 Abs. 4 Nr. 6 UStG."
    )
    return {"check": "R5_Leistungsdatum", "severity": "YELLOW", "status": status, "details": details}


def r6_creditor_master(
    vendor_name: Optional[str],
    creditors: List[Dict[str, Any]],
    vat_id: Optional[str] = None,
    iban: Optional[str] = None,
) -> Dict[str, Any]:
    creditor = match_creditor(vendor_name, vat_id, iban, creditors)
    status = "PASS" if creditor is not None else "WARN"
    creditor_id = creditor.get("_id") or creditor.get("id") if creditor else None
    details = (
        f"Vendor matched known creditor master data ID: {creditor_id}."
        if creditor is not None
        else f"Vendor '{vendor_name}' not found in creditor master data. Onboarding workflow recommended."
    )
    return {"check": "R6_Kreditorenstamm", "severity": "YELLOW", "status": status, "details": details}


def r7_account_assignment(suggestion: Dict[str, Any]) -> Dict[str, Any]:
    resolved = suggestion.get("account") is not None
    status = "PASS" if resolved else "WARN"
    details = (
        f"Plausible expense account derived from {suggestion.get('source')}: {suggestion.get('account')}."
        if resolved
        else "Expense account could not be derived unambiguously. Clerk must confirm account assignment."
    )
    return {"check": "R7_Kontierung", "severity": "YELLOW", "status": status, "details": details}


def r8_happy_path(overall_status: str) -> Dict[str, Any]:
    status = "PASS" if overall_status == "GREEN" else "FAIL"
    details = (
        "All formal, arithmetic, and master data validations passed successfully. Booking proposal generated automatically."
        if status == "PASS"
        else "One or more RED/YELLOW conditions were raised; happy-path automation is not authorized."
    )
    return {"check": "R8_Happy_Path", "severity": "GREEN", "status": status, "details": details}
