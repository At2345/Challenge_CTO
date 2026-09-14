import asyncio
import os
import sys

# Insert the backend/ dir (parent of src/) so `src` is importable as a
# package -- src/database.py uses a relative import (`from .config import
# ...`) which requires it to be loaded as `src.database`, not as a bare
# top-level `database` module.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.database import get_collection  # noqa: E402
from src.master_data import ACCOUNTS, CLIENTS, CREDITORS  # noqa: E402


async def _upsert_all(collection_name: str, documents: list) -> int:
    collection = get_collection(collection_name)
    if collection is None:
        raise RuntimeError("MongoDB is not reachable. Ensure it is running on the configured MONGO_URI.")
    count = 0
    for doc in documents:
        await collection.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
        count += 1
    return count


async def run_async() -> dict:
    accounts_count = await _upsert_all("accounts", ACCOUNTS)
    clients_count = await _upsert_all("clients", CLIENTS)
    creditors_count = await _upsert_all("creditors", CREDITORS)
    return {
        "accounts": accounts_count,
        "clients": clients_count,
        "creditors": creditors_count,
    }


def run() -> dict:
    return asyncio.run(run_async())


if __name__ == "__main__":
    result = run()
    print(f"Seed complete: {result}")
