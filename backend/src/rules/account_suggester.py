"""Step 9 (Kontierungsentscheidung): expense account assignment.

Hierarchical fallback:
1. Known creditor (matched by VAT ID, IBAN, or name) -> creditor's
   default_expense_account.
2. Semantic keyword clustering on the service description.
3. Unresolved -> triggers R7 YELLOW for clerk review.
"""
import re
from typing import Any, Dict, List, Optional

from ..master_data import ACCOUNTS

# Single source of truth for account names is master_data.py::ACCOUNTS (the
# seed data also used to populate MongoDB's `accounts` collection). Derived
# here instead of duplicated, so every account (including 1571/1576 VAT
# input and 1600 AP-collective, not just the 42xx/49xx expense accounts
# this module suggests) resolves to a name wherever it's looked up.
ACCOUNT_NAMES = {account["_id"]: account["name"] for account in ACCOUNTS}

KEYWORD_RULES = [
    ("4240", ["strom", "electricity", "gas", "wasser", "water", "fernwärme", "district heating", "energie"]),
    ("4250", ["reinigung", "cleaning", "fensterreinigung", "window washing"]),
    ("4260", ["instandhaltung", "reparatur", "maintenance", "repair", "wartung", "technischer service"]),
    ("4930", ["bürobedarf", "office supplies", "papier", "paper", "stationary", "büromaterial"]),
    ("4950", ["rechtsberatung", "legal counsel", "steuerberatung", "tax advisory", "gutachten", "expert opinion", "beratung"]),
]


def match_creditor(
    vendor_name: Optional[str],
    vat_id: Optional[str],
    iban: Optional[str],
    creditors: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    for creditor in creditors:
        if vat_id and creditor.get("vat_id") and vat_id.strip().upper() == creditor["vat_id"].strip().upper():
            return creditor
        if iban and creditor.get("iban") and iban.replace(" ", "").upper() == creditor["iban"].replace(" ", "").upper():
            return creditor
        if vendor_name and creditor.get("name") and vendor_name.strip().lower() == creditor["name"].strip().lower():
            return creditor
    # Fallback: normalized partial match ignoring legal-form suffixes; helps when vendor name
    # is shortened on letterheads/logos (e.g., 'ENERGIE').
    if vendor_name:
        def norm(s: str) -> str:
            import re
            s = re.sub(r"\\b(gmbh|mbh|ag|kg|ug|co|&|und)\\b", "", s, flags=re.IGNORECASE)
            s = re.sub(r"[^A-Za-z0-9]", "", s).lower()
            return s

        vn = norm(vendor_name)
        if len(vn) >= 6:  # avoid overly generic matches
            for creditor in creditors:
                cname = creditor.get("name") or ""
                cn = norm(cname)
                if not cn:
                    continue
                if vn in cn or cn in vn:
                    return creditor
    return None


def suggest_account(
    vendor_name: Optional[str],
    description: Optional[str],
    creditors: List[Dict[str, Any]],
    vat_id: Optional[str] = None,
    iban: Optional[str] = None,
) -> Dict[str, Any]:
    creditor = match_creditor(vendor_name, vat_id, iban, creditors)
    if creditor is not None:
        account = creditor["default_expense_account"]
        return {
            "account": account,
            "name": ACCOUNT_NAMES.get(account, account),
            "source": "creditor_master",
            "confidence": "high",
            "matched_creditor_id": creditor.get("_id") or creditor.get("id"),
        }

    haystack = f"{vendor_name or ''} {description or ''}".lower()
    for account, keywords in KEYWORD_RULES:
        for kw in keywords:
            if re.search(re.escape(kw), haystack):
                return {
                    "account": account,
                    "name": ACCOUNT_NAMES.get(account, account),
                    "source": "keyword_heuristic",
                    "confidence": "medium",
                    "matched_keyword": kw,
                }

    return {
        "account": None,
        "name": None,
        "source": "unresolved",
        "confidence": "low",
    }
