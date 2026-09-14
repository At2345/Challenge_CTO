from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .config import MONGO_URI, DATABASE_NAME

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except Exception:  # pragma: no cover
    AsyncIOMotorClient = None  # type: ignore

_client: Optional["AsyncIOMotorClient"] = None

def get_client() -> Optional["AsyncIOMotorClient"]:
    global _client
    if _client is None and AsyncIOMotorClient is not None:
        _client = AsyncIOMotorClient(MONGO_URI, serverSelectionTimeoutMS=2000)
    return _client

def get_db():
    client = get_client()
    return client[DATABASE_NAME] if client else None

def get_collection(name: str):
    db = get_db()
    return db[name] if db is not None else None

def serialize_document(doc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if doc is None:
        return None
    out = dict(doc)
    if "_id" in out:
        out["id"] = out.pop("_id")
    return out

async def log_audit_event(invoice_id: str, action: str, details: Dict[str, Any]) -> None:
    events = get_collection("audit_events")
    if events is None:
        return
    try:
        await events.insert_one(
            {
                "invoice_id": invoice_id,
                "action": action,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception:
        # Audit logging must never block the primary workflow in the MVP.
        pass
