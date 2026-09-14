"""Meta-rule orchestrator enforcing R0 precedence across R1-R8.

Given extracted invoice fields, the target client master record, and the
creditor master list, this module runs the full deterministic validation
suite and returns the traffic-light status, decision reasons, the suggested
expense account, and the blocked flag.
"""
from typing import Any, Dict, List

from . import validators as v
from .account_suggester import suggest_account


def evaluate_invoice(
    extracted: Dict[str, Any],
    client: Dict[str, Any],
    creditors: List[Dict[str, Any]],
) -> Dict[str, Any]:
    validations: List[Dict[str, Any]] = []

    validations.append(v.r1_recipient_match(extracted.get("invoice_recipient"), client))
    validations.append(v.r2_mandatory_fields(extracted))

    amounts_present = all(
        extracted.get(f) is not None for f in ("net_amount", "vat_amount", "gross_amount")
    )
    if amounts_present:
        validations.append(
            v.r3_amount_balance(extracted["net_amount"], extracted["vat_amount"], extracted["gross_amount"])
        )
    else:
        validations.append(
            {
                "check": "R3_Betragsprüfung",
                "severity": "RED",
                "status": "FAIL",
                "details": "Cannot evaluate arithmetic balance: net, VAT, or gross amount is missing.",
            }
        )

    rate_present = extracted.get("vat_rate") is not None
    if amounts_present and rate_present:
        validations.append(
            v.r4_vat_plausibility(extracted["net_amount"], extracted["vat_rate"], extracted["vat_amount"])
        )
    else:
        validations.append(
            {
                "check": "R4_USt_Plausibilität",
                "severity": "RED",
                "status": "FAIL",
                "details": "Cannot evaluate VAT plausibility: net amount, VAT rate, or VAT amount is missing.",
            }
        )

    validations.append(v.r5_service_date(extracted))
    validations.append(v.r6_creditor_master(extracted.get("vendor_name"), creditors))

    suggestion = suggest_account(extracted.get("vendor_name"), extracted.get("description"), creditors)
    validations.append(v.r7_account_assignment(suggestion))

    overall_status = v.r0_overall_status(tuple(validations))
    validations.append(v.r8_happy_path(overall_status))

    decision_reasons: List[str] = []
    for check in validations:
        if check["severity"] == "RED" and check["status"] == "FAIL":
            decision_reasons.append(f"Critical Rule Violation ({check['check'].split('_')[0]}): {check['details']}")
        elif check["severity"] == "YELLOW" and check["status"] == "WARN":
            decision_reasons.append(f"Review Required ({check['check'].split('_')[0]}): {check['details']}")

    if overall_status == "GREEN":
        decision_reasons = [
            "All formal, arithmetic, and master data validations passed successfully. Booking proposal generated automatically."
        ]
    elif overall_status == "RED":
        decision_reasons.append("Per Rule R0, critical failure overrides other indicators. Automatic ledger processing is blocked.")

    return {
        "validations": validations,
        "traffic_light": overall_status,
        "blocked": overall_status == "RED",
        "suggested_expense_account": (
            {"account": suggestion["account"], "name": suggestion["name"]} if suggestion.get("account") else None
        ),
        "decision_reasons": decision_reasons,
    }
