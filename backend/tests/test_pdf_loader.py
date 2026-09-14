from unittest.mock import patch

from src.extraction import pdf_loader
from src.extraction.pdf_loader import _score_text, extract_text_with_method

GOOD_TEXT = """
Beispiel Energie Saar GmbH
Rechnungsempfänger:
SAIAS Immobilien SPV 01 GmbH
Rechnungsnummer: INV-2026-08912
Nettobetrag: 1.000,00 EUR
"""

GARBLED_TEXT = "�~~??##  ¤¤¤ ---- ///// %%%% @@@@"

EMPTY_TEXT = "   \n\n  "


def test_score_text_prefers_recognizable_invoice_vocabulary():
    assert _score_text(GOOD_TEXT) > _score_text(GARBLED_TEXT)


def test_score_text_rejects_empty_text():
    assert _score_text(EMPTY_TEXT) < 0
    assert _score_text(None) < 0


def test_extract_text_with_method_selects_pdfplumber_for_digital_pdf():
    text, method = extract_text_with_method("backend/data/sample_invoices/invoice_01_energie_saar.pdf")
    assert method == "pdfplumber"
    assert "SAIAS Immobilien SPV 01 GmbH" in text


def test_ocr_skipped_when_both_digital_engines_are_high_confidence():
    with patch.object(pdf_loader, "_extract_with_pdfplumber", return_value=GOOD_TEXT), patch.object(
        pdf_loader, "_extract_with_pymupdf", return_value=GOOD_TEXT
    ), patch.object(pdf_loader, "_extract_with_ocr") as mock_ocr:
        text, method = extract_text_with_method("irrelevant/path.pdf")
        mock_ocr.assert_not_called()
        assert method == "pdfplumber"
        assert text == GOOD_TEXT


def test_ocr_still_runs_when_digital_engines_are_low_confidence():
    with patch.object(pdf_loader, "_extract_with_pdfplumber", return_value=GARBLED_TEXT), patch.object(
        pdf_loader, "_extract_with_pymupdf", return_value=GARBLED_TEXT
    ), patch.object(pdf_loader, "_extract_with_ocr", return_value=GOOD_TEXT) as mock_ocr:
        text, method = extract_text_with_method("irrelevant/path.pdf")
        mock_ocr.assert_called_once()
        assert method == "ocr"
        assert text == GOOD_TEXT
