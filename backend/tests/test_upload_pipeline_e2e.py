import os

import pytest
from fastapi.testclient import TestClient

from src.main import app

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sample_invoices")

client = TestClient(app)


def _upload(filename: str):
    path = os.path.join(SAMPLES_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"sample invoice not generated: {filename}")
    with open(path, "rb") as f:
        return client.post("/api/invoices/upload", files={"file": (filename, f, "application/pdf")})


def test_upload_green_energie_saar():
    resp = _upload("invoice_01_energie_saar.pdf")
    assert resp.status_code == 200
    body = resp.json()
    assert body["traffic_light"] == "GREEN"
    assert body["blocked"] is False
    assert body["extracted"]["vendor_name"] == "Beispiel Energie Saar GmbH"
    assert len(body["booking_proposal"]) == 3


def test_upload_red_arithmetic_mismatch():
    resp = _upload("invoice_03_invalid_calc.pdf")
    assert resp.status_code == 200
    body = resp.json()
    assert body["traffic_light"] == "RED"
    assert body["blocked"] is True
    assert body["booking_proposal"] == []


def test_upload_yellow_missing_service_date():
    resp = _upload("invoice_04_unknown_vendor.pdf")
    assert resp.status_code == 200
    body = resp.json()
    assert body["traffic_light"] in ("YELLOW", "GREEN")
    assert body["blocked"] is False


def test_upload_recipient_extracted_without_explicit_label():
    resp = _upload("invoice_05_immofix_no_label.pdf")
    assert resp.status_code == 200
    body = resp.json()
    assert body["extracted"]["invoice_recipient"] == "SAIAS Immobilien SPV 01 GmbH"
    assert body["extracted"]["vendor_name"] == "ImmoFix Musterservice GmbH"
    assert body["extracted"]["invoice_number"] == "IM-8842"
    assert body["extracted"]["service_date"] == "2026-09-04"


def test_upload_recipient_extracted_from_merged_von_an_header():
    resp = _upload("invoice_06_glanzwerk_von_an.pdf")
    assert resp.status_code == 200
    body = resp.json()
    extracted = body["extracted"]
    assert extracted["invoice_recipient"] == "SAIAS Immobilien SPV 01 GmbH"
    assert extracted["vendor_name"] == "Glanzwerk Musterreinigung GmbH"
    assert extracted["invoice_number"] == "GW-2026-0188"
    assert extracted["invoice_date"] == "2026-09-03"
    assert extracted["service_date"] == "2026-08-31"
    assert extracted["net_amount"] == 500.00
    assert extracted["vat_amount"] == 95.00
    assert extracted["gross_amount"] == 595.00


def test_upload_vendor_extracted_from_split_letterhead_with_merged_address():
    resp = _upload("invoice_07_jurismuster_split_letterhead.pdf")
    assert resp.status_code == 200
    body = resp.json()
    extracted = body["extracted"]
    assert extracted["vendor_name"] == "JURISMUSTER BERATUNG GMBH"
    assert extracted["invoice_recipient"] == "SAIAS Immobilien SPV 01 GmbH"
    assert extracted["invoice_number"] == "JM-2026-0447"
    assert extracted["invoice_date"] == "2026-09-05"
    assert extracted["service_date"] == "2026-09-05"
    assert extracted["net_amount"] == 2000.00
    assert extracted["vat_amount"] == 380.00
    assert extracted["gross_amount"] == 2380.00
