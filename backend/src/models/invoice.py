"""Pydantic schemas for invoice documents (extraction output, audit metadata,
and the full persisted/returned invoice record).
"""
from typing import List, Optional

from pydantic import BaseModel

from .booking import BookingLine
from .validation import ValidationResult


class ExtractedFields(BaseModel):
    invoice_recipient: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    service_date: Optional[str] = None
    currency: Optional[str] = None
    net_amount: Optional[float] = None
    vat_rate: Optional[float] = None
    vat_amount: Optional[float] = None
    gross_amount: Optional[float] = None
    description: Optional[str] = None


class SuggestedAccount(BaseModel):
    account: str
    name: str


class AuditInfo(BaseModel):
    processed_at: str
    model_or_method: str
    notes: str


class InvoiceRecord(BaseModel):
    id: str
    invoice_file: str
    original_filename: Optional[str] = None
    extracted: ExtractedFields
    validations: List[ValidationResult]
    suggested_expense_account: Optional[SuggestedAccount] = None
    traffic_light: str
    decision_reasons: List[str]
    booking_proposal: List[BookingLine]
    blocked: bool
    audit: AuditInfo


class RevalidateRequest(BaseModel):
    extracted: dict = {}
