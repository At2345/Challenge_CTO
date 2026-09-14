"""Pydantic schemas for double-entry booking proposal lines (Step 10)."""
from typing import Optional

from pydantic import BaseModel


class BookingLine(BaseModel):
    side: str
    account: str
    name: Optional[str] = None
    amount: float
