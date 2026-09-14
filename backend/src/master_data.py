"""Single source of truth for the seed/fallback master data described in the
architecture report. Used both by `data/seed_data.py` (to populate MongoDB)
and by the FastAPI service as an in-process fallback when MongoDB is
unreachable.
"""

ACCOUNTS = [
    {"_id": "1571", "name": "Abziehbare Vorsteuer 7%", "category": "Vorsteuer"},
    {"_id": "1576", "name": "Abziehbare Vorsteuer 19%", "category": "Vorsteuer"},
    {"_id": "1600", "name": "Verbindlichkeiten aus Lieferungen und Leistungen", "category": "Kreditoren-Sammelkonto"},
    {"_id": "4240", "name": "Energie / Nebenkosten", "category": "Aufwand"},
    {"_id": "4250", "name": "Reinigung", "category": "Aufwand"},
    {"_id": "4260", "name": "Instandhaltung / Reparaturen", "category": "Aufwand"},
    {"_id": "4930", "name": "Bürobedarf / Verwaltung", "category": "Aufwand"},
    {"_id": "4950", "name": "Rechts- und Beratungskosten", "category": "Aufwand"},
]

CLIENTS = [
    {
        "_id": "M0001",
        "company_name": "SAIAS Immobilien SPV 01 GmbH",
        "street": "Hafenstraße 24",
        "postal_code": "66111",
        "city": "Saarbrücken",
        "country": "Deutschland",
        "vat_id": "DE999999995",
        "currency": "EUR",
        "fiscal_year": "01.01.-31.12.",
    }
]

CREDITORS = [
    {
        "_id": "K10001",
        "name": "Beispiel Energie Saar GmbH",
        "service_category": "Energieversorgung",
        "vat_id": "DE111111117",
        "default_expense_account": "4240",
        "default_vat_rate": 19.0,
        "iban": "DE79100100100012345678",
    },
    {
        "_id": "K10002",
        "name": "ImmoFix Musterservice GmbH",
        "service_category": "Objektservice / Reparatur",
        "vat_id": "DE222222220",
        "default_expense_account": "4260",
        "default_vat_rate": 19.0,
        "iban": "DE33100100100023456789",
    },
    {
        "_id": "K10003",
        "name": "JurisMuster Beratung GmbH",
        "service_category": "Rechts- und Beratung",
        "vat_id": "DE333333339",
        "default_expense_account": "4950",
        "default_vat_rate": 19.0,
        "iban": "DE63100100100034567890",
    },
    {
        "_id": "K10004",
        "name": "OfficeMuster Handels GmbH",
        "service_category": "Bürobedarf",
        "vat_id": "DE444444443",
        "default_expense_account": "4930",
        "default_vat_rate": 19.0,
        "iban": "DE98100100100045678901",
    },
]
