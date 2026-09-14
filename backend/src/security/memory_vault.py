"""Process-isolated, volatile storage for PII surrogate mappings.

Mappings are keyed by invoice_id and held only in memory for the lifetime of
the backend process. They are never persisted to disk or MongoDB and never
transmitted across a network boundary.
"""
from threading import Lock
from typing import Dict

_lock = Lock()
_vault: Dict[str, Dict[str, str]] = {}


def store(invoice_id: str, mapping: Dict[str, str]) -> None:
    with _lock:
        _vault[invoice_id] = mapping


def retrieve(invoice_id: str) -> Dict[str, str]:
    with _lock:
        return dict(_vault.get(invoice_id, {}))


def clear(invoice_id: str) -> None:
    with _lock:
        _vault.pop(invoice_id, None)
