from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, field_validator
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.supplier import Supplier, RFQ, SupplierQuote, PurchaseOrder
from app.services.audit_logger import AuditLogger
from app.services.serial_number import SerialNumberService

router = APIRouter(prefix="/api/v1/suppliers", tags=["Suppliers"])

SERVICE_CATEGORIES = [
    "VENUE",
    "AUDIO_VISUAL",
    "CATERING",
    "DECORATION",
    "TRANSPORTATION",
    "STAFFING",
    "MARKETING",
    "MISCELLANEOUS",
]


class SupplierCreate(BaseModel):
    name_en: str
    name_ar: str | None = None
    tax_id: str | None = None
    commercial_registration: str | None = None
    email: str | None = None
    phone1: str | None = None
    phone2: str | None = None
    address_en: str | None = None
    address_ar: str | None = None
    service_category: str | None = None
    acc_key: int | None = None
    notes: str | None = None
    branch_id: int = 1

    @field_validator("service_category")
    @classmethod
    def validate_category(cls, v):
        if v and v.upper() not in SERVICE_CATEGORIES:
            raise ValueError(f"Must be one of: {', '.join(SERVICE_CATEGORIES)}")
        return v.upper() if v else v


class SupplierUpdate(BaseModel):
    name_en: str | None = None
    name_ar: str | None = None
    tax_id: str | None = None
    email: str | None = None
    phone1: str | None = None
    address_en: str | None = None
    address_ar: str | None = None
    service_category: str | None = None
    notes: str | None = None


class RFQCreate(BaseModel):
    event_id: int | None = None
    description: str | None = None
    closing_date: datetime | None = None
    currency_id: int = 1
    supplier_ids: list[int] = []


class QuoteSubmit(BaseModel):
    amount: float
    currency_id: int = 1
    conversion_rate: float = 1.0
    delivery_days: int | None = None
    valid_until: datetime | None = None
    notes: str | None = None


@router.get("")
async def list_suppliers(
    search: str | None = Query(None),
    service_category: str | None = Query(None),
    branch_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("supplier.read")),
):
    query = select(Supplier).where(Supplier.is_active)
    if branch_id:
        query = query.where(Supplier.branch_id == branch_id)
    if service_category:
        query = query.where(Supplier.service_category == service_category.upper())
    if search:
        query = query.where(
            or_(
                Supplier.name_en.ilike(f"%{search}%"),
                Supplier.name_ar.ilike(f"%{search}%"),
                Supplier.tax_id.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(Supplier.name_en)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/categories")
async def list_categories():
    return SERVICE_CATEGORIES


@router.get("/purchase-orders")
async def list_purchase_orders(
    status: str | None = Query(None),
    supplier_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("rfq.read")),
):
    query = select(PurchaseOrder)
    if status:
        query = query.where(PurchaseOrder.status == status.upper())
    if supplier_id:
        query = query.where(PurchaseOrder.supplier_id == supplier_id)
    query = query.order_by(PurchaseOrder.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/performance")
async def supplier_performance(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("report.read")),
):
    result = await db.execute(
        select(Supplier).where(Supplier.is_active).order_by(Supplier.rating.desc())
    )
    suppliers = result.scalars().all()
    return [
        {
            "id": s.id,
            "name_en": s.name_en,
            "rating": s.rating,
            "service_category": s.service_category,
            "total_pos": 0,
        }
        for s in suppliers
    ]


# === RFQ LIFECYCLE ===


@router.get("/rfqs")
async def list_rfqs(
    status: str | None = Query(None),
    event_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("rfq.read")),
):
    query = select(RFQ)
    if status:
        query = query.where(RFQ.status == status.upper())
    if event_id:
        query = query.where(RFQ.event_id == event_id)
    query = query.order_by(RFQ.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/rfqs")
async def create_rfq(
    req: RFQCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("rfq.create")),
):
    svc = SerialNumberService(db)
    rfq_number = await svc.generate("RFQ", RFQ)
    rfq = RFQ(
        rfq_number=rfq_number,
        event_id=req.event_id,
        description=req.description,
        closing_date=req.closing_date,
        currency_id=req.currency_id,
    )
    db.add(rfq)
    await db.flush()

    if req.supplier_ids:
        for sid in req.supplier_ids:
            db.add(SupplierQuote(rfq_id=rfq.id, supplier_id=sid))

    logger = AuditLogger(db)
    await logger.log(
        "CREATE", "RFQ", rfq.id, new_value=req.model_dump(), actor_id=user.id
    )
    return rfq


@router.post("/rfqs/{rfq_id}/submit-quote")
async def submit_quote(
    rfq_id: int,
    supplier_id: int = Query(...),
    req: QuoteSubmit = ...,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("rfq.read")),
):
    result = await db.execute(
        select(SupplierQuote).where(
            SupplierQuote.rfq_id == rfq_id,
            SupplierQuote.supplier_id == supplier_id,
        )
    )
    quote = result.scalar_one_or_none()
    if not quote:
        quote = SupplierQuote(rfq_id=rfq_id, supplier_id=supplier_id)
        db.add(quote)
        await db.flush()

    quote.amount = req.amount
    quote.amount_egp = req.amount * req.conversion_rate
    quote.currency_id = req.currency_id
    quote.conversion_rate = req.conversion_rate
    quote.delivery_days = req.delivery_days
    quote.valid_until = req.valid_until
    quote.notes = req.notes

    logger = AuditLogger(db)
    await logger.log("SUBMIT_QUOTE", "SupplierQuote", quote.id, actor_id=user.id)
    return quote


@router.post("/rfqs/{rfq_id}/award")
async def award_rfq(
    rfq_id: int,
    supplier_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("rfq.award")),
):
    result = await db.execute(select(RFQ).where(RFQ.id == rfq_id))
    rfq = result.scalar_one_or_none()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    quote_result = await db.execute(
        select(SupplierQuote).where(
            SupplierQuote.rfq_id == rfq_id,
            SupplierQuote.supplier_id == supplier_id,
        )
    )
    quote = quote_result.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="No quote from this supplier")

    quote.is_awarded = True
    rfq.status = "AWARDED"

    svc = SerialNumberService(db)
    po_number = await svc.generate("PO", PurchaseOrder)
    po = PurchaseOrder(
        po_number=po_number,
        rfq_id=rfq_id,
        supplier_id=supplier_id,
        event_id=rfq.event_id,
        amount=quote.amount,
        total_amount=quote.amount_egp,
        status="ISSUED",
    )
    db.add(po)
    await db.flush()

    logger = AuditLogger(db)
    await logger.log(
        "AWARD",
        "RFQ",
        rfq_id,
        new_value={"awarded_to": supplier_id, "po_id": po.id},
        actor_id=user.id,
    )
    return {"rfq_id": rfq_id, "po_id": po.id, "po_number": po.po_number}


@router.post("/")
async def create_supplier(
    req: SupplierCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("supplier.create")),
):
    svc = SerialNumberService(db)
    code = await svc.generate("SUPP", Supplier, 4)
    supplier = Supplier(code=code, **req.model_dump())
    db.add(supplier)
    await db.flush()
    logger = AuditLogger(db)
    await logger.log(
        "CREATE", "Supplier", supplier.id, new_value=req.model_dump(), actor_id=user.id
    )
    return supplier


@router.get("/{supplier_id}")
async def get_supplier(
    supplier_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("supplier.read")),
):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.put("/{supplier_id}")
async def update_supplier(
    supplier_id: int,
    req: SupplierUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("supplier.update")),
):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    old = {c.name: getattr(supplier, c.name) for c in Supplier.__table__.columns}
    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)

    logger = AuditLogger(db)
    await logger.log(
        "UPDATE",
        "Supplier",
        supplier_id,
        old_value=old,
        new_value=update_data,
        actor_id=user.id,
    )
    return {
        "id": supplier.id,
        "name_en": supplier.name_en,
        "name_ar": supplier.name_ar,
        "email": supplier.email,
        "is_active": supplier.is_active,
    }


@router.post("/{supplier_id}/rate")
async def rate_supplier(
    supplier_id: int,
    rating: float = Query(..., ge=0, le=5),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("supplier.update")),
):
    result = await db.execute(select(Supplier).where(Supplier.id == supplier_id))
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    supplier.rating = rating
    logger = AuditLogger(db)
    await logger.log(
        "RATE", "Supplier", supplier_id, new_value={"rating": rating}, actor_id=user.id
    )
    return {"id": supplier_id, "rating": rating}
