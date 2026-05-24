from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models import (
    User,
    Event,
    Client,
    Supplier,
    VendorInvoice,
    VendorInvoiceLine,
    CustomerInvoice,
    CustomerInvoiceLine,
    RCTHeader,
    RCTAllocation,
    PMTHeader,
    PMTAllocation,
    JVHeader,
    JVLine,
)

router = APIRouter(tags=["Finance & Accounting"])


# =============================================================================
# JV (Journal Vouchers)
# =============================================================================


class JVLineCreate(BaseModel):
    line_number: int
    gl_account_id: int
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    description: Optional[str] = None
    description_ar: Optional[str] = None
    event_id: Optional[int] = None


class JVCreate(BaseModel):
    jv_date: date
    reference: Optional[str] = None
    description: Optional[str] = None
    description_ar: Optional[str] = None
    event_id: Optional[int] = None
    notes: Optional[str] = None
    lines: list[JVLineCreate]


@router.post("/finance/jv")
async def create_jv(
    req: JVCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.create")),
):
    total_debit = sum(line.debit_amount for line in req.lines)
    total_credit = sum(line.credit_amount for line in req.lines)
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(
            400, detail=f"Unbalanced JV: debits={total_debit} credits={total_credit}"
        )
    if len(req.lines) < 2:
        raise HTTPException(400, detail="JV must have at least 2 lines")

    from app.services.serial_number import SerialNumberService

    sn = SerialNumberService(db)
    jv_number = await sn.generate("JV", JVHeader)

    jv = JVHeader(
        jv_number=jv_number,
        jv_date=req.jv_date,
        reference=req.reference,
        description=req.description,
        description_ar=req.description_ar,
        event_id=req.event_id,
        total_debit=total_debit,
        total_credit=total_credit,
        status="Draft",
        gl_period=req.jv_date.strftime("%Y-%m"),
        created_by=user.id,
        notes=req.notes,
    )
    db.add(jv)
    await db.flush()

    for line in req.lines:
        db.add(
            JVLine(
                jv_id=jv.id,
                line_number=line.line_number,
                gl_account_id=line.gl_account_id,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                description=line.description,
                description_ar=line.description_ar,
                event_id=line.event_id,
            )
        )

    await db.commit()
    await db.refresh(jv)
    return {"jv_id": jv.id, "jv_number": jv.jv_number, "status": "Draft"}


@router.get("/finance/jv/{jv_id}")
async def get_jv(
    jv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    result = await db.execute(
        select(JVHeader)
        .options(selectinload(JVHeader.lines))
        .where(JVHeader.id == jv_id)
    )
    jv = result.scalar_one_or_none()
    if not jv:
        raise HTTPException(404, detail="JV not found")
    return {
        "id": jv.id,
        "jv_number": jv.jv_number,
        "jv_date": jv.jv_date,
        "description": jv.description,
        "total_debit": jv.total_debit,
        "total_credit": jv.total_credit,
        "status": jv.status,
        "gl_period": jv.gl_period,
        "lines": [
            {
                "id": line.id,
                "line_number": line.line_number,
                "gl_account_id": line.gl_account_id,
                "debit_amount": line.debit_amount,
                "credit_amount": line.credit_amount,
                "description": line.description,
            }
            for line in jv.lines
        ],
    }


@router.get("/finance/jv")
async def list_jvs(
    status: Optional[str] = Query(None),
    event_id: Optional[int] = Query(None),
    period: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    query = select(JVHeader).order_by(JVHeader.created_at.desc()).limit(limit)
    if status:
        query = query.where(JVHeader.status == status)
    if event_id:
        query = query.where(JVHeader.event_id == event_id)
    if period:
        query = query.where(JVHeader.gl_period == period)
    result = await db.execute(query)
    jvs = result.scalars().all()
    return [
        {
            "id": j.id,
            "jv_number": j.jv_number,
            "jv_date": j.jv_date,
            "description": j.description,
            "total_debit": j.total_debit,
            "total_credit": j.total_credit,
            "status": j.status,
            "gl_period": j.gl_period,
        }
        for j in jvs
    ]


@router.post("/finance/jv/{jv_id}/post")
async def post_jv(
    jv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.post")),
):
    result = await db.execute(
        select(JVHeader)
        .options(selectinload(JVHeader.lines))
        .where(JVHeader.id == jv_id)
    )
    jv = result.scalar_one_or_none()
    if not jv:
        raise HTTPException(404, detail="JV not found")
    if jv.status != "Draft":
        raise HTTPException(400, detail=f"JV is already {jv.status}")

    jv.status = "Posted"
    jv.gl_posted = True
    jv.gl_posted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"jv_id": jv.id, "jv_number": jv.jv_number, "status": "Posted"}


@router.post("/finance/jv/{jv_id}/reverse")
async def reverse_jv(
    jv_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.post")),
):
    result = await db.execute(
        select(JVHeader)
        .options(selectinload(JVHeader.lines))
        .where(JVHeader.id == jv_id)
    )
    jv = result.scalar_one_or_none()
    if not jv:
        raise HTTPException(404, detail="JV not found")
    if jv.status != "Posted":
        raise HTTPException(400, detail="Can only reverse a Posted JV")

    from app.services.serial_number import SerialNumberService

    sn = SerialNumberService(db)
    reversal_number = await sn.generate("JV", JVHeader)

    reversal = JVHeader(
        jv_number=reversal_number,
        jv_date=date.today(),
        reference=f"Reversal of {jv.jv_number}",
        description=f"Reversal of {jv.jv_number}: {jv.description or ''}",
        event_id=jv.event_id,
        total_debit=jv.total_credit,
        total_credit=jv.total_debit,
        status="Posted",
        gl_posted=True,
        gl_posted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        gl_period=date.today().strftime("%Y-%m"),
        created_by=user.id,
    )
    db.add(reversal)
    await db.flush()

    for line in jv.lines:
        db.add(
            JVLine(
                jv_id=reversal.id,
                line_number=line.line_number,
                gl_account_id=line.gl_account_id,
                debit_amount=line.credit_amount,
                credit_amount=line.debit_amount,
                description=f"Reversal: {line.description or ''}",
                event_id=line.event_id,
            )
        )

    jv.status = "Reversed"
    await db.commit()
    return {
        "jv_id": reversal.id,
        "jv_number": reversal.jv_number,
        "status": "Posted (Reversal)",
    }


# =============================================================================
# AR Invoices (Customer Invoices)
# =============================================================================


class ARLineCreate(BaseModel):
    description: str
    description_ar: Optional[str] = None
    quantity: float = 1.0
    uom: Optional[str] = None
    unit_price: float = 0.0
    budget_line_id: Optional[int] = None


class ARInvoiceCreate(BaseModel):
    event_id: int
    customer_id: int
    invoice_date: date
    due_date: Optional[date] = None
    invoice_type: str = "Standard"
    notes: Optional[str] = None
    lines: list[ARLineCreate]


@router.post("/finance/ar/invoices")
async def create_ar_invoice(
    req: ARInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.create")),
):
    result = await db.execute(select(Event).where(Event.id == req.event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(404, detail="Event not found")

    result = await db.execute(select(Client).where(Client.id == req.customer_id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(404, detail="Customer not found")

    from app.services.serial_number import SerialNumberService

    sn = SerialNumberService(db)
    invoice_number = await sn.generate("INV", CustomerInvoice)

    line_total = sum(line.quantity * line.unit_price for line in req.lines)

    invoice = CustomerInvoice(
        invoice_number=invoice_number,
        event_id=req.event_id,
        customer_id=req.customer_id,
        invoice_date=req.invoice_date,
        due_date=req.due_date or req.invoice_date,
        invoice_type=req.invoice_type,
        status="Draft",
        subtotal=line_total,
        tax_amount=0.0,
        total_amount=line_total,
        amount_due=line_total,
        amount_paid=0.0,
        created_by=user.id,
        notes=req.notes,
    )
    db.add(invoice)
    await db.flush()

    for line in req.lines:
        db.add(
            CustomerInvoiceLine(
                invoice_id=invoice.id,
                budget_line_id=line.budget_line_id,
                description=line.description,
                description_ar=line.description_ar,
                quantity=line.quantity,
                uom=line.uom,
                unit_cost=0.0,
                unit_price=line.unit_price,
                line_total=line.quantity * line.unit_price,
            )
        )

    await db.commit()
    await db.refresh(invoice)
    return {
        "invoice_id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "status": "Draft",
    }


@router.get("/finance/ar/invoices")
async def list_ar_invoices(
    status: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    event_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    query = (
        select(CustomerInvoice).order_by(CustomerInvoice.created_at.desc()).limit(limit)
    )
    if status:
        query = query.where(CustomerInvoice.status == status)
    if customer_id:
        query = query.where(CustomerInvoice.customer_id == customer_id)
    if event_id:
        query = query.where(CustomerInvoice.event_id == event_id)
    result = await db.execute(query)
    invoices = result.scalars().all()
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "customer_id": inv.customer_id,
            "event_id": inv.event_id,
            "invoice_date": inv.invoice_date,
            "due_date": inv.due_date,
            "total_amount": inv.total_amount,
            "amount_due": inv.amount_due,
            "status": inv.status,
            "invoice_type": inv.invoice_type,
        }
        for inv in invoices
    ]


@router.get("/finance/ar/invoices/{invoice_id}")
async def get_ar_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    result = await db.execute(
        select(CustomerInvoice)
        .options(selectinload(CustomerInvoice.lines))
        .where(CustomerInvoice.id == invoice_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, detail="Invoice not found")
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "event_id": inv.event_id,
        "customer_id": inv.customer_id,
        "invoice_date": inv.invoice_date,
        "due_date": inv.due_date,
        "invoice_type": inv.invoice_type,
        "status": inv.status,
        "subtotal": inv.subtotal,
        "tax_amount": inv.tax_amount,
        "total_amount": inv.total_amount,
        "amount_due": inv.amount_due,
        "amount_paid": inv.amount_paid,
        "lines": [
            {
                "id": line.id,
                "description": line.description,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "line_total": line.line_total,
            }
            for line in inv.lines
        ],
    }


@router.post("/finance/ar/invoices/{invoice_id}/send")
async def send_ar_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.update")),
):
    result = await db.execute(
        select(CustomerInvoice).where(CustomerInvoice.id == invoice_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, detail="Invoice not found")
    if inv.status != "Draft":
        raise HTTPException(400, detail=f"Invoice is already {inv.status}")
    inv.status = "Sent"
    inv.sent_date = date.today()
    await db.commit()
    return {
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "status": "Sent",
    }


@router.get("/finance/ar/aging")
async def ar_aging(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    today = date.today()
    result = await db.execute(
        select(CustomerInvoice).where(
            CustomerInvoice.status.in_(["Sent", "Partial", "Overdue"])
        )
    )
    invoices = result.scalars().all()
    buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for inv in invoices:
        if inv.due_date:
            days = (today - inv.due_date).days
            if days <= 30:
                buckets["0-30"] += inv.amount_due
            elif days <= 60:
                buckets["31-60"] += inv.amount_due
            elif days <= 90:
                buckets["61-90"] += inv.amount_due
            else:
                buckets["90+"] += inv.amount_due
    return {"buckets": buckets, "total_outstanding": sum(buckets.values())}


# =============================================================================
# AP Invoices (Vendor Invoices)
# =============================================================================


class APLineCreate(BaseModel):
    description: Optional[str] = None
    quantity: float = 1.0
    uom: Optional[str] = None
    unit_price: float = 0.0
    gl_account_id: Optional[int] = None


class APInvoiceCreate(BaseModel):
    vendor_id: int
    invoice_number: str
    event_id: Optional[int] = None
    po_id: Optional[int] = None
    invoice_date: date
    due_date: Optional[date] = None
    subtotal: float = 0.0
    tax_amount: float = 0.0
    notes: Optional[str] = None
    lines: list[APLineCreate]


@router.post("/finance/ap/invoices")
async def create_ap_invoice(
    req: APInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.create")),
):
    result = await db.execute(select(Supplier).where(Supplier.id == req.vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(404, detail="Vendor not found")

    total_amount = req.subtotal + req.tax_amount
    if not req.lines:
        total = total_amount
    else:
        total = sum(line.quantity * line.unit_price for line in req.lines)

    inv = VendorInvoice(
        invoice_number=req.invoice_number,
        vendor_id=req.vendor_id,
        po_id=req.po_id,
        event_id=req.event_id,
        invoice_date=req.invoice_date,
        due_date=req.due_date or req.invoice_date,
        subtotal=req.subtotal or total,
        tax_amount=req.tax_amount,
        total_amount=total_amount or total,
        amount_due=total_amount or total,
        amount_paid=0.0,
        match_status="Pending",
        status="Unpaid",
        created_by=user.id,
        notes=req.notes,
    )
    db.add(inv)
    await db.flush()

    for line in req.lines:
        db.add(
            VendorInvoiceLine(
                invoice_id=inv.id,
                description=line.description,
                quantity=line.quantity,
                uom=line.uom,
                unit_price=line.unit_price,
                line_total=line.quantity * line.unit_price,
                gl_account_id=line.gl_account_id,
            )
        )

    await db.commit()
    await db.refresh(inv)
    return {
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "status": "Unpaid",
    }


@router.get("/finance/ap/invoices")
async def list_ap_invoices(
    status: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    match_status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    query = select(VendorInvoice).order_by(VendorInvoice.created_at.desc()).limit(limit)
    if status:
        query = query.where(VendorInvoice.status == status)
    if vendor_id:
        query = query.where(VendorInvoice.vendor_id == vendor_id)
    if match_status:
        query = query.where(VendorInvoice.match_status == match_status)
    result = await db.execute(query)
    invoices = result.scalars().all()
    return [
        {
            "id": inv.id,
            "invoice_number": inv.invoice_number,
            "vendor_id": inv.vendor_id,
            "po_id": inv.po_id,
            "invoice_date": inv.invoice_date,
            "total_amount": inv.total_amount,
            "amount_due": inv.amount_due,
            "status": inv.status,
            "match_status": inv.match_status,
        }
        for inv in invoices
    ]


@router.get("/finance/ap/invoices/{invoice_id}")
async def get_ap_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    result = await db.execute(
        select(VendorInvoice)
        .options(selectinload(VendorInvoice.lines))
        .where(VendorInvoice.id == invoice_id)
    )
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(404, detail="Invoice not found")
    return {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "vendor_id": inv.vendor_id,
        "po_id": inv.po_id,
        "event_id": inv.event_id,
        "invoice_date": inv.invoice_date,
        "due_date": inv.due_date,
        "subtotal": inv.subtotal,
        "tax_amount": inv.tax_amount,
        "total_amount": inv.total_amount,
        "amount_due": inv.amount_due,
        "amount_paid": inv.amount_paid,
        "match_status": inv.match_status,
        "variance_amount": inv.variance_amount,
        "status": inv.status,
        "lines": [
            {
                "id": line.id,
                "description": line.description,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "line_total": line.line_total,
                "qty_invoiced": line.qty_invoiced,
                "qty_received": line.qty_received,
            }
            for line in inv.lines
        ],
    }


@router.get("/finance/ap/aging")
async def ap_aging(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    today = date.today()
    result = await db.execute(
        select(VendorInvoice).where(VendorInvoice.status.in_(["Unpaid", "Partial"]))
    )
    invoices = result.scalars().all()
    buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
    for inv in invoices:
        if inv.due_date:
            days = (today - inv.due_date).days
            if days <= 30:
                buckets["0-30"] += inv.amount_due
            elif days <= 60:
                buckets["31-60"] += inv.amount_due
            elif days <= 90:
                buckets["61-90"] += inv.amount_due
            else:
                buckets["90+"] += inv.amount_due
    return {"buckets": buckets, "total_outstanding": sum(buckets.values())}


# =============================================================================
# RCT (Receipts)
# =============================================================================


class RCTAllocationCreate(BaseModel):
    invoice_id: int
    amount_allocated: float
    discount_taken: float = 0.0


class RCTCreate(BaseModel):
    customer_id: Optional[int] = None
    received_from: Optional[str] = None
    receipt_date: date
    receipt_type: str = "Cash"
    amount: float
    bank_account_id: Optional[int] = None
    check_number: Optional[str] = None
    bank_reference: Optional[str] = None
    notes: Optional[str] = None
    allocations: list[RCTAllocationCreate] = []


@router.post("/finance/rct")
async def create_receipt(
    req: RCTCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.create")),
):
    from app.services.serial_number import SerialNumberService

    sn = SerialNumberService(db)
    receipt_number = await sn.generate("RCT", RCTHeader)

    rct = RCTHeader(
        receipt_number=receipt_number,
        customer_id=req.customer_id,
        received_from=req.received_from,
        receipt_date=req.receipt_date,
        receipt_type=req.receipt_type,
        amount=req.amount,
        bank_account_id=req.bank_account_id,
        check_number=req.check_number,
        bank_reference=req.bank_reference,
        status="Open",
        created_by=user.id,
        notes=req.notes,
    )
    db.add(rct)
    await db.flush()

    total_allocated = 0
    for alloc in req.allocations:
        result = await db.execute(
            select(CustomerInvoice).where(CustomerInvoice.id == alloc.invoice_id)
        )
        inv = result.scalar_one_or_none()
        if not inv:
            raise HTTPException(404, detail=f"Invoice {alloc.invoice_id} not found")

        bal_before = inv.amount_due
        bal_after = bal_before - alloc.amount_allocated
        if bal_after < -0.01:
            raise HTTPException(
                400,
                detail=f"Allocation exceeds balance for invoice {inv.invoice_number}",
            )

        db.add(
            RCTAllocation(
                receipt_id=rct.id,
                invoice_id=alloc.invoice_id,
                amount_allocated=alloc.amount_allocated,
                discount_taken=alloc.discount_taken,
                invoice_balance_before=bal_before,
                invoice_balance_after=max(bal_after, 0),
                allocated_by=user.id,
            )
        )

        inv.amount_paid = (inv.amount_paid or 0) + alloc.amount_allocated
        inv.amount_due = max(bal_after, 0)
        if inv.amount_due <= 0:
            inv.status = "Paid"
            inv.paid_date = req.receipt_date
        else:
            inv.status = "Partial"

        total_allocated += alloc.amount_allocated

    if total_allocated > req.amount + 0.01:
        raise HTTPException(
            400,
            detail=f"Allocations ({total_allocated}) exceed receipt amount ({req.amount})",
        )

    await db.commit()
    await db.refresh(rct)
    return {
        "receipt_id": rct.id,
        "receipt_number": rct.receipt_number,
        "status": "Open",
    }


@router.get("/finance/rct")
async def list_receipts(
    customer_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    query = select(RCTHeader).order_by(RCTHeader.created_at.desc()).limit(limit)
    if customer_id:
        query = query.where(RCTHeader.customer_id == customer_id)
    if status:
        query = query.where(RCTHeader.status == status)
    result = await db.execute(query)
    receipts = result.scalars().all()
    return [
        {
            "id": r.id,
            "receipt_number": r.receipt_number,
            "customer_id": r.customer_id,
            "receipt_date": r.receipt_date,
            "receipt_type": r.receipt_type,
            "amount": r.amount,
            "status": r.status,
        }
        for r in receipts
    ]


@router.get("/finance/rct/{receipt_id}")
async def get_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    result = await db.execute(
        select(RCTHeader)
        .options(selectinload(RCTHeader.allocations))
        .where(RCTHeader.id == receipt_id)
    )
    rct = result.scalar_one_or_none()
    if not rct:
        raise HTTPException(404, detail="Receipt not found")
    return {
        "id": rct.id,
        "receipt_number": rct.receipt_number,
        "customer_id": rct.customer_id,
        "receipt_date": rct.receipt_date,
        "receipt_type": rct.receipt_type,
        "amount": rct.amount,
        "status": rct.status,
        "allocations": [
            {
                "invoice_id": a.invoice_id,
                "amount_allocated": a.amount_allocated,
                "discount_taken": a.discount_taken,
            }
            for a in rct.allocations
        ],
    }


# =============================================================================
# PMT (Payments)
# =============================================================================


class PMTAllocationCreate(BaseModel):
    invoice_id: int
    amount_allocated: float
    discount_taken: float = 0.0


class PMTCreate(BaseModel):
    vendor_id: Optional[int] = None
    paid_to: Optional[str] = None
    payment_date: date
    payment_type: str = "BankTransfer"
    amount: float
    bank_account_id: Optional[int] = None
    check_number: Optional[str] = None
    bank_reference: Optional[str] = None
    notes: Optional[str] = None
    allocations: list[PMTAllocationCreate] = []


@router.post("/finance/pmt")
async def create_payment(
    req: PMTCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.create")),
):
    from app.services.serial_number import SerialNumberService

    sn = SerialNumberService(db)
    payment_number = await sn.generate("PMT", PMTHeader)

    pmt = PMTHeader(
        payment_number=payment_number,
        vendor_id=req.vendor_id,
        paid_to=req.paid_to,
        payment_date=req.payment_date,
        payment_type=req.payment_type,
        amount=req.amount,
        bank_account_id=req.bank_account_id,
        check_number=req.check_number,
        bank_reference=req.bank_reference,
        status="Pending",
        created_by=user.id,
        notes=req.notes,
    )
    db.add(pmt)
    await db.flush()

    total_allocated = 0
    for alloc in req.allocations:
        result = await db.execute(
            select(VendorInvoice).where(VendorInvoice.id == alloc.invoice_id)
        )
        inv = result.scalar_one_or_none()
        if not inv:
            raise HTTPException(
                404, detail=f"Vendor invoice {alloc.invoice_id} not found"
            )

        bal_before = inv.amount_due
        bal_after = bal_before - alloc.amount_allocated
        if bal_after < -0.01:
            raise HTTPException(
                400,
                detail=f"Allocation exceeds balance for invoice {inv.invoice_number}",
            )

        db.add(
            PMTAllocation(
                payment_id=pmt.id,
                invoice_id=alloc.invoice_id,
                amount_allocated=alloc.amount_allocated,
                discount_taken=alloc.discount_taken,
                invoice_balance_before=bal_before,
                invoice_balance_after=max(bal_after, 0),
                allocated_by=user.id,
            )
        )

        inv.amount_paid = (inv.amount_paid or 0) + alloc.amount_allocated
        inv.amount_due = max(bal_after, 0)
        if inv.amount_due <= 0:
            inv.status = "Paid"
        else:
            inv.status = "Partial"

        total_allocated += alloc.amount_allocated

    if total_allocated > req.amount + 0.01:
        raise HTTPException(
            400,
            detail=f"Allocations ({total_allocated}) exceed payment amount ({req.amount})",
        )

    await db.commit()
    await db.refresh(pmt)
    return {
        "payment_id": pmt.id,
        "payment_number": pmt.payment_number,
        "status": "Pending",
    }


@router.get("/finance/pmt")
async def list_payments(
    vendor_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    query = select(PMTHeader).order_by(PMTHeader.created_at.desc()).limit(limit)
    if vendor_id:
        query = query.where(PMTHeader.vendor_id == vendor_id)
    if status:
        query = query.where(PMTHeader.status == status)
    result = await db.execute(query)
    payments = result.scalars().all()
    return [
        {
            "id": p.id,
            "payment_number": p.payment_number,
            "vendor_id": p.vendor_id,
            "payment_date": p.payment_date,
            "payment_type": p.payment_type,
            "amount": p.amount,
            "status": p.status,
        }
        for p in payments
    ]


@router.get("/finance/pmt/{payment_id}")
async def get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.read")),
):
    result = await db.execute(
        select(PMTHeader)
        .options(selectinload(PMTHeader.allocations))
        .where(PMTHeader.id == payment_id)
    )
    pmt = result.scalar_one_or_none()
    if not pmt:
        raise HTTPException(404, detail="Payment not found")
    return {
        "id": pmt.id,
        "payment_number": pmt.payment_number,
        "vendor_id": pmt.vendor_id,
        "payment_date": pmt.payment_date,
        "payment_type": pmt.payment_type,
        "amount": pmt.amount,
        "status": pmt.status,
        "allocations": [
            {
                "invoice_id": a.invoice_id,
                "amount_allocated": a.amount_allocated,
            }
            for a in pmt.allocations
        ],
    }


@router.post("/finance/pmt/{payment_id}/approve")
async def approve_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("finance.approve")),
):
    result = await db.execute(select(PMTHeader).where(PMTHeader.id == payment_id))
    pmt = result.scalar_one_or_none()
    if not pmt:
        raise HTTPException(404, detail="Payment not found")
    if pmt.status != "Pending":
        raise HTTPException(400, detail=f"Payment is already {pmt.status}")
    pmt.status = "Approved"
    pmt.approved_by = user.id
    pmt.approved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {
        "payment_id": pmt.id,
        "payment_number": pmt.payment_number,
        "status": "Approved",
    }
