"""
sal_router.py — Sales Invoice router for IncentiveHouse-ERP
Full CRUD + approval workflow + PDF export + payment tracking
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SalesInvoice, Client, GLAccount, User
from ..schemas.sal_schemas import (
    SalesInvoiceCreate, SalesInvoiceUpdate, SalesInvoiceOut,
    SalesInvoiceListOut, PaymentRecord,
)
from ..services.sal_service import SalesInvoiceService
from ..services.pdf_service import generate_invoice_pdf
from ..auth import get_current_user, require_role
from ..templates import templates

router = APIRouter(prefix="/sales", tags=["sales"])


# ─────────────────────────────────────────────────────────────────────────────
# LIST
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/", response_class=HTMLResponse, name="sal_router.list_invoices")
async def list_invoices(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    client_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
):
    svc = SalesInvoiceService(db)
    invoices, total = svc.list_invoices(
        status=status_filter, client_id=client_id,
        date_from=date_from, date_to=date_to,
        page=page, per_page=per_page,
    )
    summary = svc.get_summary(status=status_filter, date_from=date_from, date_to=date_to)
    clients = db.execute(select(Client).order_by(Client.client_name)).scalars().all()
    return templates.TemplateResponse("sales_list.html", {
        "request": request, "invoices": invoices,
        "summary": summary, "clients": clients,
        "status_filter": status_filter, "client_id": client_id,
        "date_from": date_from, "date_to": date_to,
        "page": page, "per_page": per_page, "total": total,
        "current_user": current_user,
    })


@router.get("/api", response_model=SalesInvoiceListOut)
async def api_list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
    client_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=200),
):
    svc = SalesInvoiceService(db)
    invoices, total = svc.list_invoices(
        status=status_filter, client_id=client_id,
        date_from=date_from, date_to=date_to,
        page=page, per_page=per_page,
    )
    return {"items": invoices, "total": total, "page": page, "per_page": per_page}


# ─────────────────────────────────────────────────────────────────────────────
# CREATE
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/new", response_class=HTMLResponse)
async def new_invoice_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clients     = db.execute(select(Client).order_by(Client.client_name)).scalars().all()
    gl_accounts = db.execute(select(GLAccount).order_by(GLAccount.account_code)).scalars().all()
    return templates.TemplateResponse("sales_form.html", {
        "request": request, "invoice": None,
        "clients": clients, "gl_accounts": gl_accounts,
        "today": date.today().isoformat(),
        "current_user": current_user,
    })


@router.post("/", response_model=SalesInvoiceOut, name="sal_router.create_invoice")
async def create_invoice(
    data: SalesInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = SalesInvoiceService(db)
    invoice = svc.create(data, created_by=current_user.id)
    return invoice


# ─────────────────────────────────────────────────────────────────────────────
# READ
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{id}", response_class=HTMLResponse)
async def view_invoice(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc     = SalesInvoiceService(db)
    invoice = svc.get_or_404(id)
    clients     = db.execute(select(Client).order_by(Client.client_name)).scalars().all()
    gl_accounts = db.execute(select(GLAccount).order_by(GLAccount.account_code)).scalars().all()
    return templates.TemplateResponse("sales_form.html", {
        "request": request, "invoice": invoice,
        "clients": clients, "gl_accounts": gl_accounts,
        "today": date.today().isoformat(),
        "current_user": current_user,
    })


@router.get("/api/{id}", response_model=SalesInvoiceOut)
async def api_get_invoice(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SalesInvoiceService(db).get_or_404(id)


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/api/{id}", response_model=SalesInvoiceOut, name="sal_router.update_invoice")
async def update_invoice(
    id: int,
    data: SalesInvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc     = SalesInvoiceService(db)
    invoice = svc.get_or_404(id)
    if invoice.status == "approved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Approved invoices cannot be edited")
    return svc.update(invoice, data, updated_by=current_user.id)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE
# ─────────────────────────────────────────────────────────────────────────────
@router.delete("/api/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    svc     = SalesInvoiceService(db)
    invoice = svc.get_or_404(id)
    if invoice.status == "approved":
        raise HTTPException(status.HTTP_409_CONFLICT, "Approved invoices cannot be deleted. Void instead.")
    svc.delete(invoice)


# ─────────────────────────────────────────────────────────────────────────────
# APPROVAL WORKFLOW
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/api/{id}/submit")
async def submit_invoice(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc     = SalesInvoiceService(db)
    invoice = svc.transition(id, from_status="draft", to_status="submitted", user=current_user)
    return {"id": id, "status": invoice.status}


@router.post("/api/{id}/approve")
async def approve_invoice(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    svc     = SalesInvoiceService(db)
    invoice = svc.transition(id, from_status="submitted", to_status="approved", user=current_user)
    return {"id": id, "status": invoice.status}


@router.post("/api/{id}/reject")
async def reject_invoice(
    id: int,
    reason: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager", "admin")),
):
    svc     = SalesInvoiceService(db)
    invoice = svc.transition(id, from_status="submitted", to_status="rejected",
                             user=current_user, reason=reason)
    return {"id": id, "status": invoice.status, "reason": reason}


@router.post("/api/{id}/void")
async def void_invoice(
    id: int,
    reason: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    svc     = SalesInvoiceService(db)
    invoice = svc.void(id, user=current_user, reason=reason)
    return {"id": id, "status": invoice.status}


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT TRACKING
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/api/{id}/payments", response_model=SalesInvoiceOut)
async def record_payment(
    id: int,
    payment: PaymentRecord,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = SalesInvoiceService(db)
    return svc.record_payment(id, payment, user=current_user)


@router.get("/api/{id}/payments")
async def get_payments(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = SalesInvoiceService(db)
    svc.get_or_404(id)
    return svc.get_payments(id)


# ─────────────────────────────────────────────────────────────────────────────
# PDF EXPORT
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{id}/pdf", name="sal_router.export_pdf")
async def export_pdf(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc     = SalesInvoiceService(db)
    invoice = svc.get_or_404(id)
    pdf_bytes = generate_invoice_pdf(invoice)
    filename  = f"invoice_{invoice.invoice_number}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY / REPORTING
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/api/summary/by-status")
async def summary_by_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    return SalesInvoiceService(db).summary_by_status(date_from=date_from, date_to=date_to)


@router.get("/api/summary/by-client")
async def summary_by_client(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    limit: int = Query(10, ge=1, le=100),
):
    return SalesInvoiceService(db).summary_by_client(
        date_from=date_from, date_to=date_to, limit=limit
    )


@router.get("/api/overdue")
async def get_overdue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SalesInvoiceService(db).get_overdue()
