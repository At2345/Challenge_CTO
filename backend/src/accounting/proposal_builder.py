"""Step 10 (Buchungssatz erstellen): balanced double-entry booking proposal.

Debit: expense account (net_amount) + input VAT account (vat_amount).
Credit: accounts payable collective account 1600 (gross_amount).
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ..master_data import ACCOUNTS
from ..utils.numbers import parse_decimal

VAT_ACCOUNTS = {
    19: "1576",
    7: "1571",
}

AP_COLLECTIVE_ACCOUNT = "1600"

# Single source of truth for account names is master_data.py::ACCOUNTS.
_ACCOUNT_NAMES = {account["_id"]: account["name"] for account in ACCOUNTS}


def _vat_account_for_rate(vat_rate: Any) -> str:
    rate = float(parse_decimal(vat_rate))
    closest = min(VAT_ACCOUNTS.keys(), key=lambda r: abs(r - rate))
    return VAT_ACCOUNTS[closest]


def build_booking_proposal(
    net_amount: Any,
    vat_amount: Any,
    vat_rate: Any,
    gross_amount: Any,
    expense_account: Optional[str],
) -> List[Dict[str, Any]]:
    if expense_account is None:
        return []

    net_d = parse_decimal(net_amount)
    vat_d = parse_decimal(vat_amount)
    gross_d = parse_decimal(gross_amount)
    vat_account = _vat_account_for_rate(vat_rate)

    def _line(side: str, account: str, amount: Decimal) -> Dict[str, Any]:
        return {
            "side": side,
            "account": account,
            "name": _ACCOUNT_NAMES.get(account, account),
            "amount": float(amount),
        }

    return [
        _line("DEBIT", expense_account, net_d),
        _line("DEBIT", vat_account, vat_d),
        _line("CREDIT", AP_COLLECTIVE_ACCOUNT, gross_d),
    ]


def is_balanced(booking_proposal: List[Dict[str, Any]], tolerance: Decimal = Decimal("0.02")) -> bool:
    debit_total = sum(parse_decimal(l["amount"]) for l in booking_proposal if l["side"] == "DEBIT")
    credit_total = sum(parse_decimal(l["amount"]) for l in booking_proposal if l["side"] == "CREDIT")
    return abs(debit_total - credit_total) <= tolerance
