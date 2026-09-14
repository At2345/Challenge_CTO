from src.master_data import CLIENTS, CREDITORS
from src.rules.engine import evaluate_invoice
from src.accounting.proposal_builder import build_booking_proposal, is_balanced

CLIENT = CLIENTS[0]


def test_green_scenario_energie_saar():
    extracted = {
        "invoice_recipient": "SAIAS Immobilien SPV 01 GmbH",
        "vendor_name": "Beispiel Energie Saar GmbH",
        "invoice_number": "INV-2026-08912",
        "invoice_date": "2026-03-15",
        "service_date": "2026-02-28",
        "currency": "EUR",
        "net_amount": 1000.00,
        "vat_rate": 19.0,
        "vat_amount": 190.00,
        "gross_amount": 1190.00,
        "description": "Stromlieferung Liegenschaft Hafenstraße",
    }
    result = evaluate_invoice(extracted, CLIENT, CREDITORS)
    assert result["traffic_light"] == "GREEN"
    assert result["blocked"] is False
    assert result["suggested_expense_account"]["account"] == "4240"

    proposal = build_booking_proposal(
        extracted["net_amount"], extracted["vat_amount"], extracted["vat_rate"],
        extracted["gross_amount"], result["suggested_expense_account"]["account"],
    )
    assert is_balanced(proposal)
    credit_line = next(l for l in proposal if l["side"] == "CREDIT")
    assert credit_line["account"] == "1600"
    assert credit_line["amount"] == 1190.00
    assert credit_line["name"] == "Verbindlichkeiten aus Lieferungen und Leistungen"


def test_red_scenario_arithmetic_mismatch():
    extracted = {
        "invoice_recipient": "SAIAS Immobilien SPV 01 GmbH",
        "vendor_name": "ImmoFix Musterservice GmbH",
        "invoice_number": "IF-9921",
        "invoice_date": "2026-03-18",
        "service_date": "2026-03-10",
        "currency": "EUR",
        "net_amount": 500.00,
        "vat_rate": 19.0,
        "vat_amount": 95.00,
        "gross_amount": 620.00,
        "description": "Reparatur Klingelanlage Eingangsbereich",
    }
    result = evaluate_invoice(extracted, CLIENT, CREDITORS)
    assert result["traffic_light"] == "RED"
    assert result["blocked"] is True


def test_red_scenario_recipient_mismatch():
    extracted = {
        "invoice_recipient": "Some Other Company GmbH",
        "vendor_name": "Beispiel Energie Saar GmbH",
        "invoice_number": "INV-1",
        "invoice_date": "2026-01-01",
        "service_date": "2026-01-01",
        "currency": "EUR",
        "net_amount": 100.00,
        "vat_rate": 19.0,
        "vat_amount": 19.00,
        "gross_amount": 119.00,
        "description": "Strom",
    }
    result = evaluate_invoice(extracted, CLIENT, CREDITORS)
    assert result["traffic_light"] == "RED"
    assert result["blocked"] is True


def test_yellow_scenario_unknown_creditor_and_missing_service_date():
    extracted = {
        "invoice_recipient": "SAIAS Immobilien SPV 01 GmbH",
        "vendor_name": "Unbekannter Dienstleister GmbH",
        "invoice_number": "INV-2",
        "invoice_date": "2026-01-01",
        "service_date": None,
        "currency": "EUR",
        "net_amount": 100.00,
        "vat_rate": 19.0,
        "vat_amount": 19.00,
        "gross_amount": 119.00,
        "description": "Bürobedarf Lieferung",
    }
    result = evaluate_invoice(extracted, CLIENT, CREDITORS)
    assert result["traffic_light"] == "YELLOW"
    assert result["blocked"] is False
