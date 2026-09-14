from src.security.anonymizer import (
    sanitize,
    reidentify,
    validate_de_vat_checksum,
    validate_iban_checksum,
)


def test_de_vat_checksum_valid():
    assert validate_de_vat_checksum("DE999999995") is True


def test_de_vat_checksum_invalid():
    assert validate_de_vat_checksum("DE123456789") is False


def test_iban_checksum_valid():
    assert validate_iban_checksum("DE79100100100012345678") is True


def test_iban_checksum_invalid():
    assert validate_iban_checksum("DE00100100100012345678") is False


def test_sanitize_and_reidentify_round_trip():
    text = (
        "Rechnungsempfänger: SAIAS Immobilien SPV 01 GmbH\n"
        "USt-IdNr: DE999999995\n"
        "IBAN: DE79100100100012345678\n"
        "Kontakt: buchhaltung@example.com"
    )
    sanitized, mapping = sanitize(text)
    assert "DE999999995" not in sanitized
    assert "DE79100100100012345678" not in sanitized
    assert "buchhaltung@example.com" not in sanitized
    assert "<VAT_ID_1>" in sanitized
    assert "<IBAN_1>" in sanitized
    assert "<EMAIL_1>" in sanitized

    restored = reidentify(sanitized, mapping)
    assert restored == text


def test_sanitize_ignores_invalid_checksum_vat_id():
    text = "USt-IdNr: DE123456789"
    sanitized, mapping = sanitize(text)
    assert sanitized == text
    assert mapping == {}
