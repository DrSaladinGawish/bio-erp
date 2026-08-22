from datetime import date, datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    code: str
    name_en: str
    name_ar: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    tax_id: Optional[str] = None
    credit_limit: float = 0.0
    risk_rating: str = "B"
    payment_terms: int = 30
    discount_pct: float = 0.0
    discount_days: int = 0
    currency_id: int = 1
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    credit_limit: Optional[float] = None
    risk_rating: Optional[str] = None
    payment_terms: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class CustomerResponse(BaseModel):
    id: int; code: str; name_en: str; name_ar: Optional[str] = None
    email: Optional[str] = None; phone: Optional[str] = None
    tax_id: Optional[str] = None; credit_limit: float; credit_used: float
    risk_rating: str; payment_terms: int; discount_pct: float
    status: str; created_at: datetime


class InvoiceLineCreate(BaseModel):
    description: Optional[str] = None
    quantity: float = 1.0
    unit_price: float = 0.0
    discount_pct: float = 0.0
    tax_rate: float = 0.0
    gl_account_id: Optional[int] = None


class InvoiceLineResponse(BaseModel):
    id: int; line_number: int; description: Optional[str] = None
    quantity: float; unit_price: float; net_amount: float
    tax_amount: float; total_amount: float


class InvoiceCreate(BaseModel):
    customer_id: int
    invoice_date: date
    due_date: date
    currency_id: int = 1
    exchange_rate: float = 1.0
    notes: Optional[str] = None
    lines: List[InvoiceLineCreate] = Field(..., min_length=1)


class InvoiceResponse(BaseModel):
    id: int; invoice_number: str; customer_id: int
    invoice_date: date; due_date: date; status: str
    subtotal: float; tax_amount: float; total_amount: float
    paid_amount: float; balance_due: float; journal_id: Optional[int] = None
    lines: List[InvoiceLineResponse] = []
    created_at: datetime


class PaymentCreate(BaseModel):
    customer_id: int
    invoice_id: Optional[int] = None
    payment_date: date
    amount: float = Field(..., gt=0)
    payment_method: str = "bank"
    reference: Optional[str] = None
    currency_id: int = 1
    exchange_rate: float = 1.0
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int; payment_number: str; invoice_id: Optional[int] = None
    customer_id: int; payment_date: date; amount: float
    payment_method: str; reference: Optional[str] = None
    journal_id: Optional[int] = None; created_at: datetime


class CreditNoteCreate(BaseModel):
    invoice_id: Optional[int] = None
    customer_id: int
    credit_date: date
    amount: float = Field(..., gt=0)
    reason: str = "other"
    notes: Optional[str] = None


class CreditNoteResponse(BaseModel):
    id: int; credit_note_number: str; invoice_id: Optional[int] = None
    customer_id: int; credit_date: date; amount: float
    reason: Optional[str] = None; status: str; journal_id: Optional[int] = None
    created_at: datetime


class AgingBucketResponse(BaseModel):
    bucket: str; total_amount: float; invoice_count: int


class AgingResponse(BaseModel):
    customer_id: int; customer_name: str
    total_outstanding: float; buckets: List[AgingBucketResponse]
    as_of_date: date


class StatementLine(BaseModel):
    date: date; description: str; reference: str
    debit: float; credit: float; balance: float


class StatementResponse(BaseModel):
    customer_id: int; customer_name: str
    period_start: date; period_end: date
    opening_balance: float; closing_balance: float
    lines: List[StatementLine]


class MessageResponse(BaseModel):
    message: str; id: Optional[int] = None


class HealthResponse(BaseModel):
    status: str; module: str = "far-ar"; version: str = "1.0.0"
    customers: int = 0; invoices: int = 0; payments: int = 0
