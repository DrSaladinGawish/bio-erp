from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_sync_session
from app.organs.far_ap_organ import schemas
from app.organs.far_ap_organ.service import (
    VendorService, BillService, PaymentService,
    CreditNoteService, AgingService, HealthService,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["far-ap"])


def get_db():
    db = get_sync_session()
    try:
        yield db
    finally:
        db.close()


def _ok(msg: str, id: Optional[int] = None) -> schemas.MessageResponse:
    return schemas.MessageResponse(message=msg, id=id)


@router.post("/vendors", response_model=schemas.VendorResponse, status_code=201)
def create_vendor(data: schemas.VendorCreate, db: Session = Depends(get_db)):
    svc = VendorService(db)
    try:
        v = svc.create(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.VendorResponse(id=v.id, code=v.code, name_en=v.name_en, name_ar=v.name_ar,
        email=v.email, phone=v.phone, tax_id=v.tax_id, payment_terms=v.payment_terms,
        risk_rating=v.risk_rating, status=v.status.value, created_at=v.created_at)


@router.get("/vendors", response_model=List[schemas.VendorResponse])
def list_vendors(status: Optional[str] = Query(None), db: Session = Depends(get_db)):
    svc = VendorService(db)
    return [schemas.VendorResponse(id=v.id, code=v.code, name_en=v.name_en, name_ar=v.name_ar,
        email=v.email, phone=v.phone, tax_id=v.tax_id, payment_terms=v.payment_terms,
        risk_rating=v.risk_rating, status=v.status.value, created_at=v.created_at)
        for v in svc.list(status)]


@router.get("/vendors/{vendor_id}", response_model=schemas.VendorResponse)
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    svc = VendorService(db)
    v = svc.get(vendor_id)
    if not v:
        raise HTTPException(404, "Vendor not found")
    return schemas.VendorResponse(id=v.id, code=v.code, name_en=v.name_en, name_ar=v.name_ar,
        email=v.email, phone=v.phone, tax_id=v.tax_id, payment_terms=v.payment_terms,
        risk_rating=v.risk_rating, status=v.status.value, created_at=v.created_at)


@router.put("/vendors/{vendor_id}", response_model=schemas.VendorResponse)
def update_vendor(vendor_id: int, data: schemas.VendorUpdate, db: Session = Depends(get_db)):
    svc = VendorService(db)
    try:
        v = svc.update(vendor_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return schemas.VendorResponse(id=v.id, code=v.code, name_en=v.name_en, name_ar=v.name_ar,
        email=v.email, phone=v.phone, tax_id=v.tax_id, payment_terms=v.payment_terms,
        risk_rating=v.risk_rating, status=v.status.value, created_at=v.created_at)


@router.post("/bills", response_model=schemas.BillResponse, status_code=201)
def create_bill(data: schemas.BillCreate, user_id: int = Query(0), db: Session = Depends(get_db)):
    svc = BillService(db)
    try:
        b = svc.create(data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _bill_response(b)


@router.post("/bills/{bill_id}/approve", response_model=schemas.BillResponse)
def approve_bill(bill_id: int, data: schemas.ApproveAction, user_id: int = Query(0), db: Session = Depends(get_db)):
    svc = BillService(db)
    try:
        b = svc.approve(bill_id, data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _bill_response(b)


@router.get("/bills", response_model=List[schemas.BillResponse])
def list_bills(
    vendor_id: Optional[int] = Query(None), status: Optional[str] = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    svc = BillService(db)
    bills, total = svc.list(vendor_id, status, page, page_size)
    return [_bill_response(b) for b in bills]


@router.get("/bills/{bill_id}", response_model=schemas.BillResponse)
def get_bill(bill_id: int, db: Session = Depends(get_db)):
    svc = BillService(db)
    b = svc.get(bill_id)
    if not b:
        raise HTTPException(404, "Bill not found")
    return _bill_response(b)


def _bill_response(b):
    return schemas.BillResponse(id=b.id, bill_number=b.bill_number, vendor_id=b.vendor_id,
        bill_date=b.bill_date, due_date=b.due_date, status=b.status.value,
        subtotal=b.subtotal, tax_amount=b.tax_amount, total_amount=b.total_amount,
        paid_amount=b.paid_amount, balance_due=b.balance_due, journal_id=b.journal_id,
        approved_by=b.approved_by, approved_at=b.approved_at,
        lines=[schemas.BillLineResponse(id=l.id, line_number=l.line_number,
            description=l.description, quantity=l.quantity, unit_price=l.unit_price,
            net_amount=l.net_amount, tax_amount=l.tax_amount, total_amount=l.total_amount)
            for l in (b.lines or [])], created_at=b.created_at)


@router.post("/payments", response_model=schemas.PaymentResponse, status_code=201)
def create_payment(data: schemas.PaymentCreate, user_id: int = Query(0), db: Session = Depends(get_db)):
    svc = PaymentService(db)
    try:
        p = svc.create(data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.PaymentResponse(id=p.id, payment_number=p.payment_number, bill_id=p.bill_id,
        vendor_id=p.vendor_id, payment_date=p.payment_date, amount=p.amount,
        payment_method=p.payment_method.value, reference=p.reference, journal_id=p.journal_id,
        created_at=p.created_at)


@router.get("/payments", response_model=List[schemas.PaymentResponse])
def list_payments(vendor_id: Optional[int] = Query(None), page: int = Query(1, ge=1),
                  page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    svc = PaymentService(db)
    payments, total = svc.list(vendor_id, page, page_size)
    return [schemas.PaymentResponse(id=p.id, payment_number=p.payment_number, bill_id=p.bill_id,
        vendor_id=p.vendor_id, payment_date=p.payment_date, amount=p.amount,
        payment_method=p.payment_method.value, reference=p.reference, journal_id=p.journal_id,
        created_at=p.created_at) for p in payments]


@router.post("/credit-notes", response_model=schemas.CreditNoteResponse, status_code=201)
def create_credit_note(data: schemas.CreditNoteCreate, user_id: int = Query(0), db: Session = Depends(get_db)):
    svc = CreditNoteService(db)
    try:
        cn = svc.create(data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.CreditNoteResponse(id=cn.id, credit_note_number=cn.credit_note_number,
        bill_id=cn.bill_id, vendor_id=cn.vendor_id, credit_date=cn.credit_date,
        amount=cn.amount, reason=cn.reason, status=cn.status.value, journal_id=cn.journal_id,
        created_at=cn.created_at)


@router.get("/credit-notes", response_model=List[schemas.CreditNoteResponse])
def list_credit_notes(vendor_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    svc = CreditNoteService(db)
    return [schemas.CreditNoteResponse(id=cn.id, credit_note_number=cn.credit_note_number,
        bill_id=cn.bill_id, vendor_id=cn.vendor_id, credit_date=cn.credit_date,
        amount=cn.amount, reason=cn.reason, status=cn.status.value, journal_id=cn.journal_id,
        created_at=cn.created_at) for cn in svc.list(vendor_id)]


@router.get("/aging/{vendor_id}")
def get_aging(vendor_id: int, as_of: Optional[date] = Query(None), db: Session = Depends(get_db)):
    svc = AgingService(db)
    try:
        return svc.calculate(vendor_id, as_of)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/approval-queue")
def get_approval_queue(db: Session = Depends(get_db)):
    svc = BillService(db)
    return svc.list_approval_queue()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    return HealthService(db).check()
