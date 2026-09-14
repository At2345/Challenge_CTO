from src.accounting.proposal_builder import build_booking_proposal, is_balanced


def test_booking_proposal_balances_19_percent():
    proposal = build_booking_proposal(1000.00, 190.00, 19.0, 1190.00, "4240")
    assert is_balanced(proposal)
    debit_accounts = {l["account"] for l in proposal if l["side"] == "DEBIT"}
    assert debit_accounts == {"4240", "1576"}
    credit = next(l for l in proposal if l["side"] == "CREDIT")
    assert credit["account"] == "1600"
    assert credit["amount"] == 1190.00
    # Every line -- expense, VAT input, and AP-collective -- must resolve a
    # human-readable name from master_data.py::ACCOUNTS, not just the code.
    names_by_account = {l["account"]: l["name"] for l in proposal}
    assert names_by_account["4240"] == "Energie / Nebenkosten"
    assert names_by_account["1576"] == "Abziehbare Vorsteuer 19%"
    assert names_by_account["1600"] == "Verbindlichkeiten aus Lieferungen und Leistungen"


def test_booking_proposal_balances_7_percent():
    proposal = build_booking_proposal(200.00, 14.00, 7.0, 214.00, "4930")
    assert is_balanced(proposal)
    debit_accounts = {l["account"] for l in proposal if l["side"] == "DEBIT"}
    assert debit_accounts == {"4930", "1571"}
    names_by_account = {l["account"]: l["name"] for l in proposal}
    assert names_by_account["4930"] == "Bürobedarf / Verwaltung"
    assert names_by_account["1571"] == "Abziehbare Vorsteuer 7%"


def test_booking_proposal_empty_when_no_account():
    proposal = build_booking_proposal(100.00, 19.00, 19.0, 119.00, None)
    assert proposal == []
