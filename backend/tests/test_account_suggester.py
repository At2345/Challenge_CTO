from src.master_data import ACCOUNTS, CREDITORS
from src.rules.account_suggester import ACCOUNT_NAMES, suggest_account, match_creditor


def test_account_names_cover_all_master_data_accounts():
    # ACCOUNT_NAMES must be derived from master_data.ACCOUNTS (single source
    # of truth), not a hand-maintained partial copy -- otherwise accounts
    # like 1571/1576/1600 (referenced directly by proposal_builder.py, not
    # via suggest_account) silently resolve to no name.
    for account in ACCOUNTS:
        assert ACCOUNT_NAMES[account["_id"]] == account["name"]


def test_match_creditor_by_name():
    creditor = match_creditor("Beispiel Energie Saar GmbH", None, None, CREDITORS)
    assert creditor is not None
    assert creditor["_id"] == "K10001"


def test_suggest_account_from_creditor_master():
    suggestion = suggest_account("Beispiel Energie Saar GmbH", "Stromlieferung", CREDITORS)
    assert suggestion["account"] == "4240"
    assert suggestion["source"] == "creditor_master"


def test_suggest_account_from_keyword_heuristic():
    suggestion = suggest_account("Unbekannter Lieferant GmbH", "Rechtsberatung zu Mietvertrag", [])
    assert suggestion["account"] == "4950"
    assert suggestion["source"] == "keyword_heuristic"


def test_suggest_account_unresolved():
    suggestion = suggest_account("Unbekannt GmbH", "Sonstige Leistungen", [])
    assert suggestion["account"] is None
    assert suggestion["source"] == "unresolved"
