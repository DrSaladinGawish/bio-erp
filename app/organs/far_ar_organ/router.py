from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_sync_session
from app.organs.far_ar_organ import schemas
from app.organs.far_ar_organ.service import (
    CustomerService, InvoiceService, PaymentService,
    CreditNoteService, AgingService, StatementService, HealthService,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["far-ar"])


def get_db():
    db = get_sync_session()
    try:
        yield db
    finally:
        db.close()


def _ok(msg: str, id: Optional[int] = None) -> schemas.MessageResponse:
    return schemas.MessageResponse(message=msg, id=id)


@router.post("/customers", response_model=schemas.CustomerResponse, status_code=201)
def create_customer(data: schemas.CustomerCreate, db: Session = Depends(get_db)):
    svc = CustomerService(db)
    try:
        c = svc.create(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.CustomerResponse(id=c.id, code=c.code, name_en=c.name_en, name_ar=c.name_ar,
        email=c.email, phone=c.phone, tax_id=c.tax_id, credit_limit=c.credit_limit,
        credit_used=c.credit_used, risk_rating=c.risk_rating, payment_terms=c.payment_terms,
        discount_pct=c.discount_pct, status=c.status.value, created_at=c.created_at)


@router.get("/customers", response_model=List[schemas.CustomerResponse])
def list_customers(status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    svc = CustomerService(db)
    return [schemas.CustomerResponse(id=c.id, code=c.code, name_en=c.name_en, name_ar=c.name_ar,
        email=c.email, phone=c.phone, tax_id=c.tax_id, credit_limit=c.credit_limit,
        credit_used=c.credit_used, risk_rating=c.risk_rating, payment_terms=c.payment_terms,
        discount_pct=c.discount_pct, status=c.status.value, created_at=c.created_at)
        for c in svc.list(status)]


@router.get("/customers/{customer_id}", response_model=schemas.CustomerResponse)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    svc = CustomerService(db)
    c = svc.get(customer_id)
    if not c:
        raise HTTPException(404, "Customer not found")
    return schemas.CustomerResponse(id=c.id, code=c.code, name_en=c.name_en, name_ar=c.name_ar,
        email=c.email, phone=c.phone, tax_id=c.tax_id, credit_limit=c.credit_limit,
        credit_used=c.credit_used, risk_rating=c.risk_rating, payment_terms=c.payment_terms,
        discount_pct=c.discount_pct, status=c.status.value, created_at=c.created_at)


@router.put("/customers/{customer_id}", response_model=schemas.CustomerResponse)
def update_customer(customer_id: int, data: schemas.CustomerUpdate, db: Session = Depends(get_db)):
    svc = CustomerService(db)
    try:
        c = svc.update(customer_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return schemas.CustomerResponse(id=c.id, code=c.code, name_en=c.name_en, name_ar=c.name_ar,
        email=c.email, phone=c.phone, tax_id=c.tax_id, credit_limit=c.credit_limit,
        credit_used=c.credit_used, risk_rating=c.risk_rating, payment_terms=c.payment_terms,
        discount_pct=c.discount_pct, status=c.status.value, created_at=c.created_at)


@router.get("/customers/{customer_id}/credit-check")
def check_credit(customer_id: int, amount: float = Query(...), db: Session = Depends(get_db)):
    svc = CustomerService(db)
    try:
        return svc.check_credit(customer_id, amount)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/invoices", response_model=schemas.InvoiceResponse, status_code=201)
def create_invoice(data: schemas.InvoiceCreate, user_id: int = Query(0), db: Session = Depends(get_db)):
    svc = InvoiceService(db)
    try:
        inv = svc.create(data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _invoice_response(inv)


@router.post("/invoices/{invoice_id}/send", response_model=schemas.InvoiceResponse)
def send_invoice(invoice_id: int, user_id: int = Query(0), db: Session = Depends(get_db)):
    svc = InvoiceService(db)
    try:
        inv = svc.send(invoice_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _invoice_response(inv)


@router.get("/invoices", response_model=List[schemas.InvoiceResponse])
def list_invoices(
    customer_id: Optional[int] = Query(None), status: Optional[str] = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    svc = InvoiceService(db)
    invoices, total = svc.list(customer_id, status, page, page_size)
    return [_invoice_response(i) for i in invoices]


@router.get("/invoices/{invoice_id}", response_model=schemas.InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    svc = InvoiceService(db)
    inv = svc.get(invoice_id)
    if not inv:
        raise HTTPException(404, "Invoice not found")
    return _invoice_response(inv)


def _invoice_response(inv):
    return schemas.InvoiceResponse(id=inv.id, invoice_number=inv.invoice_number,
        customer_id=inv.customer_id, invoice_date=inv.invoice_date, due_date=inv.due_date,
        status=inv.status.value, subtotal=inv.subtotal, tax_amount=inv.tax_amount,
        total_amount=inv.total_amount, paid_amount=inv.paid_amount, balance_due=inv.balance_due,
        journal_id=inv.journal_id,
        lines=[schemas.InvoiceLineResponse(id=l.id, line_number=l.line_number,
            description=l.description, quantity=l.quantity, unit_price=l.unit_price,
            net_amount=l.net_amount, tax_amount=l.tax_amount, total_amount=l.total_amount)
            for l in (inv.lines or [])],
        created_at=inv.created_at)


@router.post("/payments", response_model=schemas.PaymentResponse, status_code=201)
def create_payment(data: schemas.PaymentCreate, user_id: int = Query(0), db: Session = Depends(get_db)):
    svc = PaymentService(db)
    try:
        p = svc.create(data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.PaymentResponse(id=p.id, payment_number=p.payment_number,
        invoice_id=p.invoice_id, customer_id=p.customer_id, payment_date=p.payment_date,
        amount=p.amount, payment_method=p.payment_method.value, reference=p.reference,
        journal_id=p.journal_id, created_at=p.created_at)


@router.get("/payments", response_model=List[schemas.PaymentResponse])
def list_payments(
    customer_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    svc = PaymentService(db)
    payments, total = svc.list(customer_id, page, page_size)
    return [schemas.PaymentResponse(id=p.id, payment_number=p.payment_number,
        invoice_id=p.invoice_id, customer_id=p.customer_id, payment_date=p.payment_date,
        amount=p.amount, payment_method=p.payment_method.value, reference=p.reference,
        journal_id=p.journal_id, created_at=p.created_at) for p in payments]


@router.post("/credit-notes", response_model=schemas.CreditNoteResponse, status_code=201)
def create_credit_note(data: schemas.CreditNoteCreate, user_id: int = Query(0), db: Session = Depends(get_db)):
    svc = CreditNoteService(db)
    try:
        cn = svc.create(data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.CreditNoteResponse(id=cn.id, credit_note_number=cn.credit_note_number,
        invoice_id=cn.invoice_id, customer_id=cn.customer_id, credit_date=cn.credit_date,
        amount=cn.amount, reason=cn.reason, status=cn.status.value, journal_id=cn.journal_id,
        created_at=cn.created_at)


@router.get("/credit-notes", response_model=List[schemas.CreditNoteResponse])
def list_credit_notes(customer_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    svc = CreditNoteService(db)
    return [schemas.CreditNoteResponse(id=cn.id, credit_note_number=cn.credit_note_number,
        invoice_id=cn.invoice_id, customer_id=cn.customer_id, credit_date=cn.credit_date,
        amount=cn.amount, reason=cn.reason, status=cn.status.value, journal_id=cn.journal_id,
        created_at=cn.created_at) for cn in svc.list(customer_id)]


@router.get("/aging/{customer_id}", response_model=schemas.AgingResponse)
def get_aging(customer_id: int, as_of: Optional[date] = Query(None), db: Session = Depends(get_db)):
    svc = AgingService(db)
    try:
        result = svc.calculate(customer_id, as_of)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return schemas.AgingResponse(customer_id=result["customer_id"],
        customer_name=result["customer_name"],
        total_outstanding=result["total_outstanding"],
        buckets=[schemas.AgingBucketResponse(bucket=k, total_amount=v, invoice_count=0)
                 for k, v in result["buckets"].items()],
        as_of_date=result["as_of_date"])


@router.get("/aging-overdue")
def get_overdue(days: int = Query(1, ge=0), db: Session = Depends(get_db)):
    svc = AgingService(db)
    return svc.get_overdue(days)


@router.get("/customers/{customer_id}/statement")
def get_statement(
    customer_id: int, period_start: date = Query(...), period_end: date = Query(...),
    db: Session = Depends(get_db),
):
    svc = StatementService(db)
    try:
        result = svc.generate(customer_id, period_start, period_end)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return result


@router.get("/health", response_model=schemas.HealthResponse)
def health_check(db: Session = Depends(get_db)):
    return HealthService(db).check()
