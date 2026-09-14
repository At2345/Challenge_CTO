from src.extraction.field_extractor import extract_fields

SAMPLE_TEXT = """
Beispiel Energie Saar GmbH
Rechnungsempfänger:
SAIAS Immobilien SPV 01 GmbH

Rechnungsnummer: INV-2026-08912
Rechnungsdatum: 15.03.2026
Leistungsdatum: 28.02.2026

Leistungsbeschreibung: Stromlieferung Liegenschaft Hafenstraße Abrechnungsmonat Februar 2026

Nettobetrag: 1.000,00 EUR
USt.-Satz: 19,0 %
USt.-Betrag: 190,00 EUR
Gesamtbetrag: 1.190,00 EUR
"""


def test_extract_fields_from_sample_invoice():
    fields = extract_fields(SAMPLE_TEXT)
    assert fields["invoice_recipient"] == "SAIAS Immobilien SPV 01 GmbH"
    assert fields["invoice_number"] == "INV-2026-08912"
    assert fields["invoice_date"] == "2026-03-15"
    assert fields["service_date"] == "2026-02-28"
    assert fields["currency"] == "EUR"
    assert fields["net_amount"] == 1000.00
    assert fields["vat_rate"] == 19.0
    assert fields["vat_amount"] == 190.00
    assert fields["gross_amount"] == 1190.00


# Two-column header row collapsed onto a single physical text line by PDF
# extraction (no wide whitespace gap preserved between columns), with the
# recipient label and invoice number sharing one line.
TWO_COLUMN_TEXT = """
ENERGIE
Beispiel Energie Saar GmbH
Musterweg 10 · 66113 Saarbrücken
Rechnungsempfänger Rechnungs-Nr. BES-2026-0901
SAIAS Immobilien SPV 01 GmbH Ausgestellt am 02.09.2026
Hafenstraße 24 Fällig am 16.09.2026
66111 Saarbrücken
Kundennr. K-430018
Abrechnungszeitraum Leistungsdatum
01.08.2026 - 31.08.2026 31.08.2026
Nettobetrag 1.000,00 EUR
Umsatzsteuer 19 % 190,00 EUR
Rechnungsbetrag 1.190,00 EUR
"""


def test_extract_recipient_survives_single_space_column_merge():
    fields = extract_fields(TWO_COLUMN_TEXT)
    assert fields["invoice_recipient"] == "SAIAS Immobilien SPV 01 GmbH"


# No explicit "Rechnungsempfänger"/"Empfänger" label at all; recipient must
# be inferred via the legal-form-suffix fallback. Invoice number uses bare
# "Rechnung:" and the VAT rate is followed by the spelled-out word
# "Umsatzsteuer" rather than the USt/MwSt siglum.
LABEL_LESS_TEXT = """
ImmoFix Musterservice GmbH
Handwerkerstraße 18 · 66115 Saarbrücken
ImmoFix Musterservice GmbH · Handwerkerstraße 18 · 66115 Saarbrücken
Rechnung: IM-8842
SAIAS Immobilien SPV 01 GmbH
Hafenstraße 24 Datum: 04.09.2026
66111 Saarbrücken
Kundenkonto: SPV01-220
Zahlbar bis: 18.09.2026
Rechnung für Reparaturarbeiten

Reparatur Beleuchtung Treppenhaus und Austausch von zwei Leuchtmitteln 800,00 EUR

Zwischensumme 800,00 EUR
zzgl. 19 % Umsatzsteuer 152,00 EUR
Rechnungsbetrag 952,00 EUR
"""


def test_extract_fields_without_explicit_recipient_label():
    fields = extract_fields(LABEL_LESS_TEXT)
    assert fields["vendor_name"] == "ImmoFix Musterservice GmbH"
    assert fields["invoice_recipient"] == "SAIAS Immobilien SPV 01 GmbH"
    assert fields["invoice_number"] == "IM-8842"
    assert fields["invoice_date"] == "2026-09-04"
    assert fields["net_amount"] == 800.00
    assert fields["vat_rate"] == 19.0
    assert fields["vat_amount"] == 152.00
    assert fields["gross_amount"] == 952.00


def test_service_date_falls_back_to_generic_datum_label():
    # No "Leistungsdatum"/"Leistungszeitraum" present, only a generic "Datum:".
    fields = extract_fields(LABEL_LESS_TEXT)
    assert fields["service_date"] == "2026-09-04"


# Merged two-column "VON AN" header row (no colons, no "Rechnungsempfänger"
# label); the vendor's own tagline line partially echoes its legal name,
# which previously caused the recipient fallback to pick the vendor's
# tagline (or the entire merged vendor+recipient row) instead of the
# actual recipient.
VON_AN_TEXT = """
Rechnung GW-2026-0188
GLANZWERK
Musterreinigung GmbH 03.09.2026
VON AN
Glanzwerk Musterreinigung GmbH SAIAS Immobilien SPV 01 GmbH
Beispielallee 7 Hafenstraße 24
66117 Saarbrücken 66111 Saarbrücken
Unterhaltsreinigung
Objekt Saarbrücken · Leistungsdatum 31.08.2026
Beschreibung Menge Betrag
Unterhaltsreinigung Objekt - August 2026 1 500,00 EUR
Netto 500,00 EUR
19 % USt. 95,00 EUR
Gesamt 595,00 EUR
Zahlungsziel: 17.09.2026
IBAN DE86100100100056789012 · USt-IdNr. DE777777773 · EUR
"""


def test_extract_recipient_from_merged_von_an_header_row():
    fields = extract_fields(VON_AN_TEXT)
    assert fields["invoice_recipient"] == "SAIAS Immobilien SPV 01 GmbH"


def test_extract_fields_from_merged_von_an_header_row():
    fields = extract_fields(VON_AN_TEXT)
    assert fields["vendor_name"] == "Glanzwerk Musterreinigung GmbH"
    assert fields["invoice_recipient"] == "SAIAS Immobilien SPV 01 GmbH"
    assert fields["invoice_number"] == "GW-2026-0188"
    assert fields["invoice_date"] == "2026-09-03"
    assert fields["service_date"] == "2026-08-31"
    assert fields["net_amount"] == 500.00
    assert fields["vat_rate"] == 19.0
    assert fields["vat_amount"] == 95.00
    assert fields["gross_amount"] == 595.00
    assert fields["description"] == "Unterhaltsreinigung Objekt - August 2026"


# Letterhead with the vendor's own company name split across two lines by
# font-size styling ("JURISMUSTER" logo line, "BERATUNG GMBH" beneath it in
# all caps), each merged with a neighboring address column
# ("Kanzleiplatz 3" / "66119 Saarbrücken") by PDF text extraction. No
# "Lieferant:"/"Von:" label and no "Von ... An ..." header. Previously the
# naive first-non-trivial-line fallback captured "JURISMUSTER Kanzleiplatz
# 3" (an address fragment) as the vendor name instead of the actual
# company name, and the all-caps "GMBH" legal-form suffix was also missed
# by a case-sensitive check.
SPLIT_LETTERHEAD_TEXT = """
JURISMUSTER Kanzleiplatz 3
BERATUNG GMBH 66119 Saarbrücken

Honorarrechnung
Rechnungsnummer: JM-2026-0447
Rechnungsdatum: 05.09.2026
Leistungsdatum: 05.09.2026

Rechnungsempfänger:
SAIAS Immobilien SPV 01 GmbH
Hafenstraße 24
66111 Saarbrücken

Leistungsbeschreibung: Vertragsprüfung und schriftliche Stellungnahme

Nettobetrag: 2.000,00 EUR
USt.-Satz: 19,0 %
USt.-Betrag: 380,00 EUR
Gesamtbetrag: 2.380,00 EUR
"""


def test_extract_vendor_from_split_letterhead_with_merged_address():
    fields = extract_fields(SPLIT_LETTERHEAD_TEXT)
    assert fields["vendor_name"] == "JURISMUSTER BERATUNG GMBH"
    assert fields["invoice_recipient"] == "SAIAS Immobilien SPV 01 GmbH"
    assert fields["invoice_number"] == "JM-2026-0447"
    assert fields["invoice_date"] == "2026-09-05"
    assert fields["service_date"] == "2026-09-05"
    assert fields["net_amount"] == 2000.00
    assert fields["vat_rate"] == 19.0
    assert fields["vat_amount"] == 380.00
    assert fields["gross_amount"] == 2380.00


def test_service_date_fallback_does_not_match_compound_date_labels():
    # "Rechnungsdatum"/"Abrechnungsdatum" must not be mistaken for the bare
    # "Datum" fallback label -- only an explicit Leistungsdatum should count.
    text = """
    Beispiel Energie Saar GmbH
    Rechnungsempfänger:
    SAIAS Immobilien SPV 01 GmbH
    Rechnungsnummer: INV-2026-08912
    Rechnungsdatum: 15.03.2026
    Abrechnungsdatum: 01.03.2026
    Nettobetrag: 1.000,00 EUR
    """
    fields = extract_fields(text)
    assert fields["service_date"] is None
