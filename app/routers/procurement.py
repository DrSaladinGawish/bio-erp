from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.procurement import GRNHeader, GRNDetail, ServiceConfirmation
from app.models.supplier import PurchaseOrder, Supplier
from app.services.serial_number import SerialNumberService

router = APIRouter(prefix="/api/v1/procurement", tags=["Procurement"])


# --- GRN Detail Schemas ---


class GRNDetailCreate(BaseModel):
    po_line_id: int | None = None
    description: str | None = None
    ordered_qty: float = 0.0
    received_qty: float = 0.0
    accepted_qty: float = 0.0
    rejected_qty: float = 0.0
    rejection_reason: str | None = None
    condition: str = "Good"
    inspection_notes: str | None = None


class GRNCreate(BaseModel):
    po_id: int
    supplier_id: int
    event_id: int | None = None
    grn_date: date
    received_by: int | None = None
    delivery_note_no: str | None = None
    warehouse_location: str | None = None
    notes: str | None = None
    lines: list[GRNDetailCreate]


# --- GRN Endpoints ---


@router.post("/grn")
async def create_grn(
    req: GRNCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("procurement.create")),
):
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == req.po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(404, detail="Purchase Order not found")

    result = await db.execute(select(Supplier).where(Supplier.id == req.supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(404, detail="Supplier not found")

    sn = SerialNumberService(db)
    grn_number = await sn.generate("GRN", GRNHeader)

    grn = GRNHeader(
        grn_number=grn_number,
        po_id=req.po_id,
        supplier_id=req.supplier_id,
        event_id=req.event_id or po.event_id,
        grn_date=req.grn_date,
        received_by=req.received_by,
        delivery_note_no=req.delivery_note_no,
        warehouse_location=req.warehouse_location,
        status="Pending",
        notes=req.notes,
    )
    db.add(grn)
    await db.flush()

    for line in req.lines:
        db.add(
            GRNDetail(
                grn_id=grn.id,
                po_line_id=line.po_line_id,
                description=line.description,
                ordered_qty=line.ordered_qty,
                received_qty=line.received_qty,
                accepted_qty=line.accepted_qty,
                rejected_qty=line.rejected_qty,
                rejection_reason=line.rejection_reason,
                condition=line.condition,
                inspection_notes=line.inspection_notes,
            )
        )

    po.status = "GRN_Partial"
    all_full = all(
        d.accepted_qty >= d.ordered_qty for d in req.lines if d.ordered_qty > 0
    )
    if all_full and req.lines:
        po.status = "GRN_Complete"

    await db.commit()
    await db.refresh(grn)
    return {"grn_id": grn.id, "grn_number": grn.grn_number, "status": "Pending"}


@router.get("/grn")
async def list_grns(
    po_id: int | None = Query(None),
    supplier_id: int | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("procurement.read")),
):
    query = select(GRNHeader).order_by(GRNHeader.created_at.desc()).limit(limit)
    if po_id:
        query = query.where(GRNHeader.po_id == po_id)
    if supplier_id:
        query = query.where(GRNHeader.supplier_id == supplier_id)
    if status:
        query = query.where(GRNHeader.status == status)
    result = await db.execute(query)
    grns = result.scalars().all()
    return [
        {
            "id": g.id,
            "grn_number": g.grn_number,
            "po_id": g.po_id,
            "supplier_id": g.supplier_id,
            "grn_date": g.grn_date,
            "status": g.status,
        }
        for g in grns
    ]


@router.get("/grn/{grn_id}")
async def get_grn(
    grn_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("procurement.read")),
):
    result = await db.execute(
        select(GRNHeader)
        .options(selectinload(GRNHeader.lines))
        .where(GRNHeader.id == grn_id)
    )
    grn = result.scalar_one_or_none()
    if not grn:
        raise HTTPException(404, detail="GRN not found")
    return {
        "id": grn.id,
        "grn_number": grn.grn_number,
        "po_id": grn.po_id,
        "supplier_id": grn.supplier_id,
        "event_id": grn.event_id,
        "grn_date": grn.grn_date,
        "status": grn.status,
        "lines": [
            {
                "id": line.id,
                "description": line.description,
                "ordered_qty": line.ordered_qty,
                "received_qty": line.received_qty,
                "accepted_qty": line.accepted_qty,
                "rejected_qty": line.rejected_qty,
                "condition": line.condition,
            }
            for line in grn.lines
        ],
    }


@router.post("/grn/{grn_id}/approve")
async def approve_grn(
    grn_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("procurement.approve")),
):
    result = await db.execute(select(GRNHeader).where(GRNHeader.id == grn_id))
    grn = result.scalar_one_or_none()
    if not grn:
        raise HTTPException(404, detail="GRN not found")
    if grn.status != "Pending":
        raise HTTPException(400, detail=f"GRN is already {grn.status}")
    grn.status = "Approved"
    await db.commit()
    return {"grn_id": grn.id, "grn_number": grn.grn_number, "status": "Approved"}


# --- Service Confirmation Endpoints ---


class ServiceConfirmationCreate(BaseModel):
    po_id: int
    supplier_id: int
    event_id: int | None = None
    service_description: str
    completion_date: date
    quality_rating: int = 3
    performance_notes: str | None = None
    confirmed_by: int | None = None


@router.post("/service-confirmations")
async def create_service_confirmation(
    req: ServiceConfirmationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("procurement.create")),
):
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == req.po_id)
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(404, detail="Purchase Order not found")

    sc = ServiceConfirmation(
        po_id=req.po_id,
        supplier_id=req.supplier_id,
        event_id=req.event_id or po.event_id,
        service_description=req.service_description,
        completion_date=req.completion_date,
        quality_rating=req.quality_rating,
        performance_notes=req.performance_notes,
        confirmed_by=req.confirmed_by or user.id,
        status="Confirmed",
    )
    db.add(sc)
    await db.commit()
    await db.refresh(sc)
    return {"id": sc.id, "status": "Confirmed"}


@router.get("/service-confirmations")
async def list_service_confirmations(
    po_id: int | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("procurement.read")),
):
    query = (
        select(ServiceConfirmation)
        .order_by(ServiceConfirmation.created_at.desc())
        .limit(limit)
    )
    if po_id:
        query = query.where(ServiceConfirmation.po_id == po_id)
    result = await db.execute(query)
    scs = result.scalars().all()
    return [
        {
            "id": s.id,
            "po_id": s.po_id,
            "service_description": s.service_description,
            "completion_date": s.completion_date,
            "quality_rating": s.quality_rating,
            "status": s.status,
        }
        for s in scs
    ]
