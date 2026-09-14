"""Pydantic schemas for R0-R8 rule audit entries."""
from typing import Optional

from pydantic import BaseModel


class ValidationResult(BaseModel):
    check: str
    severity: str
    status: str
    details: str
    delta: Optional[float] = None
