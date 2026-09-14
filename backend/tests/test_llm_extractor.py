import json
from types import SimpleNamespace

import pytest

from src import config
from src.extraction import llm_extractor


@pytest.fixture(autouse=True)
def _reset_config(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    yield


def test_is_enabled_false_without_api_key():
    assert llm_extractor.is_enabled() is False


def test_extract_fields_llm_returns_none_when_disabled():
    assert llm_extractor.extract_fields_llm("some invoice text") is None


def _fake_openai_response(payload: dict):
    message = SimpleNamespace(content=json.dumps(payload))
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def test_extract_fields_llm_success(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")

    payload = {
        "invoice_recipient": "SAIAS Immobilien SPV 01 GmbH",
        "vendor_name": "Beispiel Energie Saar GmbH",
        "invoice_number": "INV-2026-08912",
        "invoice_date": "2026-03-15",
        "service_date": "2026-02-28",
        "currency": "EUR",
        "net_amount": "1.000,00",
        "vat_rate": 19.0,
        "vat_amount": 190.0,
        "gross_amount": 1190.0,
        "description": "Stromlieferung Februar 2026",
    }

    class FakeCompletions:
        def create(self, **kwargs):
            return _fake_openai_response(payload)

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, api_key, base_url):
            self.chat = FakeChat()

    monkeypatch.setattr("openai.OpenAI", FakeClient)

    result = llm_extractor.extract_fields_llm("irrelevant sanitized text")
    assert result is not None
    assert result["vendor_name"] == "Beispiel Energie Saar GmbH"
    assert result["invoice_date"] == "2026-03-15"
    # German-formatted amount string coerced to float via parse_decimal
    assert result["net_amount"] == 1000.0
    assert result["vat_amount"] == 190.0
    assert result["gross_amount"] == 1190.0


def test_extract_fields_llm_returns_none_on_invalid_json(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")

    class FakeCompletions:
        def create(self, **kwargs):
            message = SimpleNamespace(content="not json at all")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, api_key, base_url):
            self.chat = FakeChat()

    monkeypatch.setattr("openai.OpenAI", FakeClient)

    assert llm_extractor.extract_fields_llm("text") is None


def test_extract_fields_llm_returns_none_on_request_exception(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")

    class FakeCompletions:
        def create(self, **kwargs):
            raise RuntimeError("network error")

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, api_key, base_url):
            self.chat = FakeChat()

    monkeypatch.setattr("openai.OpenAI", FakeClient)

    assert llm_extractor.extract_fields_llm("text") is None


def test_extract_fields_llm_strips_markdown_code_fence(monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")
    payload = {"vendor_name": "ImmoFix Musterservice GmbH"}
    fenced = "```json\n" + json.dumps(payload) + "\n```"

    class FakeCompletions:
        def create(self, **kwargs):
            message = SimpleNamespace(content=fenced)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        def __init__(self, api_key, base_url):
            self.chat = FakeChat()

    monkeypatch.setattr("openai.OpenAI", FakeClient)

    result = llm_extractor.extract_fields_llm("text")
    assert result is not None
    assert result["vendor_name"] == "ImmoFix Musterservice GmbH"
