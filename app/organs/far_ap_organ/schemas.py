from datetime import date, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class VendorCreate(BaseModel):
    code: str; name_en: str; name_ar: Optional[str] = None
    email: Optional[str] = None; phone: Optional[str] = None
    tax_id: Optional[str] = None; payment_terms: int = 30
    risk_rating: str = "B"; currency_id: int = 1; notes: Optional[str] = None


class VendorUpdate(BaseModel):
    name_en: Optional[str] = None; name_ar: Optional[str] = None
    email: Optional[str] = None; phone: Optional[str] = None
    payment_terms: Optional[int] = None; risk_rating: Optional[str] = None
    status: Optional[str] = None; notes: Optional[str] = None


class VendorResponse(BaseModel):
    id: int; code: str; name_en: str; name_ar: Optional[str] = None
    email: Optional[str] = None; phone: Optional[str] = None
    tax_id: Optional[str] = None; payment_terms: int; risk_rating: str
    status: str; created_at: datetime


class BillLineCreate(BaseModel):
    description: Optional[str] = None; quantity: float = 1.0
    unit_price: float = 0.0; discount_pct: float = 0.0
    tax_rate: float = 0.0; gl_account_id: Optional[int] = None


class BillLineResponse(BaseModel):
    id: int; line_number: int; description: Optional[str] = None
    quantity: float; unit_price: float; net_amount: float
    tax_amount: float; total_amount: float


class BillCreate(BaseModel):
    vendor_id: int; bill_date: date; due_date: date
    currency_id: int = 1; exchange_rate: float = 1.0
    notes: Optional[str] = None; lines: List[BillLineCreate] = Field(..., min_length=1)


class BillResponse(BaseModel):
    id: int; bill_number: str; vendor_id: int
    bill_date: date; due_date: date; status: str
    subtotal: float; tax_amount: float; total_amount: float
    paid_amount: float; balance_due: float; journal_id: Optional[int] = None
    approved_by: Optional[int] = None; approved_at: Optional[datetime] = None
    lines: List[BillLineResponse] = []; created_at: datetime


class PaymentCreate(BaseModel):
    vendor_id: int; bill_id: Optional[int] = None
    payment_date: date; amount: float = Field(..., gt=0)
    payment_method: str = "bank"; reference: Optional[str] = None
    currency_id: int = 1; exchange_rate: float = 1.0; notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int; payment_number: str; bill_id: Optional[int] = None
    vendor_id: int; payment_date: date; amount: float
    payment_method: str; reference: Optional[str] = None
    journal_id: Optional[int] = None; created_at: datetime


class CreditNoteCreate(BaseModel):
    bill_id: Optional[int] = None; vendor_id: int
    credit_date: date; amount: float = Field(..., gt=0)
    reason: str = "other"; notes: Optional[str] = None


class CreditNoteResponse(BaseModel):
    id: int; credit_note_number: str; bill_id: Optional[int] = None
    vendor_id: int; credit_date: date; amount: float
    reason: Optional[str] = None; status: str; journal_id: Optional[int] = None; created_at: datetime


class AgingBucketResponse(BaseModel):
    bucket: str; total_amount: float; invoice_count: int


class AgingResponse(BaseModel):
    vendor_id: int; vendor_name: str; total_outstanding: float
    buckets: List[AgingBucketResponse]; as_of_date: date


class ApprovalQueueItem(BaseModel):
    id: int; bill_id: int; bill_number: str; vendor_name: str
    total_amount: float; status: str; created_at: datetime


class ApproveAction(BaseModel):
    approved: bool = True; notes: Optional[str] = None


class MessageResponse(BaseModel):
    message: str; id: Optional[int] = None


class HealthResponse(BaseModel):
    status: str; module: str = "far-ap"; version: str = "1.0.0"
    vendors: int = 0; bills: int = 0; payments: int = 0
