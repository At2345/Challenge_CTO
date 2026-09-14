"""Generates four synthetic invoice PDFs for local testing of the
upload -> extraction -> rules -> booking pipeline. Uses PyMuPDF (already a
backend dependency) to render simple text-based invoices matching the
label conventions understood by extraction/field_extractor.py.
"""
import os

import fitz  # PyMuPDF

OUT_DIR = os.path.dirname(__file__)


def _write_pdf(filename: str, lines: list) -> None:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=11)
        y += 18
    doc.save(os.path.join(OUT_DIR, filename))
    doc.close()


SAMPLES = {
    "invoice_01_energie_saar.pdf": [
        "Beispiel Energie Saar GmbH",
        "Rechnungsempfänger:",
        "SAIAS Immobilien SPV 01 GmbH",
        "",
        "Rechnungsnummer: INV-2026-08912",
        "Rechnungsdatum: 15.03.2026",
        "Leistungsdatum: 28.02.2026",
        "",
        "Leistungsbeschreibung: Stromlieferung Liegenschaft Hafenstrasse Februar 2026",
        "",
        "Nettobetrag: 1.000,00 EUR",
        "USt.-Satz: 19,0 %",
        "USt.-Betrag: 190,00 EUR",
        "Gesamtbetrag: 1.190,00 EUR",
    ],
    "invoice_02_immofix_ok.pdf": [
        "ImmoFix Musterservice GmbH",
        "Rechnungsempfänger:",
        "SAIAS Immobilien SPV 01 GmbH",
        "",
        "Rechnungsnummer: IF-1001",
        "Rechnungsdatum: 10.03.2026",
        "Leistungsdatum: 05.03.2026",
        "",
        "Leistungsbeschreibung: Reparatur Klingelanlage Eingangsbereich",
        "",
        "Nettobetrag: 500,00 EUR",
        "USt.-Satz: 19,0 %",
        "USt.-Betrag: 95,00 EUR",
        "Gesamtbetrag: 595,00 EUR",
    ],
    "invoice_03_invalid_calc.pdf": [
        "ImmoFix Musterservice GmbH",
        "Rechnungsempfänger:",
        "SAIAS Immobilien SPV 01 GmbH",
        "",
        "Rechnungsnummer: IF-9921",
        "Rechnungsdatum: 18.03.2026",
        "Leistungsdatum: 10.03.2026",
        "",
        "Leistungsbeschreibung: Reparatur Klingelanlage Eingangsbereich",
        "",
        "Nettobetrag: 500,00 EUR",
        "USt.-Satz: 19,0 %",
        "USt.-Betrag: 95,00 EUR",
        "Gesamtbetrag: 620,00 EUR",
    ],
    "invoice_04_unknown_vendor.pdf": [
        "OfficeMuster Handels GmbH",
        "Rechnungsempfänger:",
        "SAIAS Immobilien SPV 01 GmbH",
        "",
        "Rechnungsnummer: OM-3001",
        "Rechnungsdatum: 01.03.2026",
        "",
        "Leistungsbeschreibung: Büromaterial Lieferung März 2026",
        "",
        "Nettobetrag: 150,00 EUR",
        "USt.-Satz: 19,0 %",
        "USt.-Betrag: 28,50 EUR",
        "Gesamtbetrag: 178,50 EUR",
    ],
    # No explicit "Rechnungsempfänger" label; recipient is inferred from the
    # legal-form-suffix heuristic. Uses "Rechnung:" (not "Rechnungs-Nr.") for
    # the invoice number, and spells out "Umsatzsteuer" instead of the
    # USt/MwSt siglum after the VAT percentage.
    "invoice_05_immofix_no_label.pdf": [
        "ImmoFix Musterservice GmbH",
        "Handwerkerstraße 18 · 66115 Saarbrücken",
        "ImmoFix Musterservice GmbH · Handwerkerstraße 18 · 66115 Saarbrücken",
        "Rechnung: IM-8842",
        "SAIAS Immobilien SPV 01 GmbH",
        "Hafenstraße 24 Datum: 04.09.2026",
        "66111 Saarbrücken",
        "Kundenkonto: SPV01-220",
        "Zahlbar bis: 18.09.2026",
        "Rechnung für Reparaturarbeiten",
        "",
        "Reparatur Beleuchtung Treppenhaus und Austausch von zwei Leuchtmitteln 800,00 EUR",
        "",
        "Zwischensumme 800,00 EUR",
        "zzgl. 19 % Umsatzsteuer 152,00 EUR",
        "Rechnungsbetrag 952,00 EUR",
    ],
    # Merged two-column "VON AN" header row (vendor/recipient side-by-side,
    # no colons, no "Rechnungsempfänger" label). The vendor's own tagline
    # line ("Musterreinigung GmbH ...") partially echoes its legal name,
    # which previously caused the recipient fallback to misfire.
    "invoice_06_glanzwerk_von_an.pdf": [
        "Rechnung GW-2026-0188",
        "GLANZWERK",
        "Musterreinigung GmbH 03.09.2026",
        "VON AN",
        "Glanzwerk Musterreinigung GmbH SAIAS Immobilien SPV 01 GmbH",
        "Beispielallee 7 Hafenstraße 24",
        "66117 Saarbrücken 66111 Saarbrücken",
        "Unterhaltsreinigung",
        "Objekt Saarbrücken · Leistungsdatum 31.08.2026",
        "Beschreibung Menge Betrag",
        "Unterhaltsreinigung Objekt - August 2026 1 500,00 EUR",
        "Netto 500,00 EUR",
        "19 % USt. 95,00 EUR",
        "Gesamt 595,00 EUR",
        "Zahlungsziel: 17.09.2026",
        "IBAN DE86100100100056789012 · USt-IdNr. DE777777773 · EUR",
    ],
    # Letterhead with the company's own name split across two lines by
    # font-size styling ("JURISMUSTER" logo line, "BERATUNG GMBH" beneath
    # it), with a neighboring address column merged onto each of those two
    # lines ("Kanzleiplatz 3" / "66119 Saarbrücken"). No "Lieferant:"/"Von:"
    # label and no "Von ... An ..." header -- the vendor's letterhead is
    # simply the first block on the page, previously mistaken for
    # "JURISMUSTER Kanzleiplatz 3" by the naive first-line fallback.
    "invoice_07_jurismuster_split_letterhead.pdf": [
        "JURISMUSTER Kanzleiplatz 3",
        "BERATUNG GMBH 66119 Saarbrücken",
        "",
        "Honorarrechnung",
        "Rechnungsnummer: JM-2026-0447",
        "Rechnungsdatum: 05.09.2026",
        "Leistungsdatum: 05.09.2026",
        "",
        "Rechnungsempfänger:",
        "SAIAS Immobilien SPV 01 GmbH",
        "Hafenstraße 24",
        "66111 Saarbrücken",
        "",
        "Leistungsbeschreibung: Vertragsprüfung und schriftliche Stellungnahme",
        "",
        "Nettobetrag: 2.000,00 EUR",
        "USt.-Satz: 19,0 %",
        "USt.-Betrag: 380,00 EUR",
        "Gesamtbetrag: 2.380,00 EUR",
    ],
}


def run() -> list:
    created = []
    for filename, lines in SAMPLES.items():
        _write_pdf(filename, lines)
        created.append(filename)
    return created


if __name__ == "__main__":
    print(f"Generated: {run()}")
