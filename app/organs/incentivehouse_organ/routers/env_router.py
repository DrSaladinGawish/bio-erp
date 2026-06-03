"""
ENV Router — Reference Data (Master Tables) & Dashboard
========================================================
End-points (prefix ``/api/v1/env``):

  GET  /staff                       — list staff
  GET  /staff/{id}                  — single staff record
  POST /staff                       — create staff
  GET  /clients                     — list clients (clients_mtbl)
  GET  /clients/{id}                — single client
  POST /clients                     — create client
  GET  /vendors                     — list vendors (vendors_mtbl)
  GET  /vendors/{id}                — single vendor
  POST /vendors                     — create vendor
  GET  /cost-centers                — list cost centres
  GET  /cost-centers/{id}           — single cost centre
  POST /cost-centers                — create cost centre
  GET  /pnr-dim                     — list PNR records (pnr_records)
  GET  /pnr-dim/{id}                — single PNR
  POST /pnr-dim                     — create PNR
  GET  /dashboard                   — top-level dashboard rollup
  GET  /search                      — cross-table quick search
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models_production import (
    Staff, Vendor, Event,
    SalesInvoice, PurchaseOrder, VendorInvoice, SalesLineItem,
    StaffAssignment,
)
from ..models_production import (
    Client, CostCenter, PnrRecord,
)
from ..schemas import PaginatedResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/env", tags=["ENV Reference Data"])


# ── Pydantic models (Staff) ────────────────────────────────────────────

class StaffCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    code: Optional[str] = None
    name: str
    role: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    hire_date: Optional[date] = None
    cost_center: Optional[str] = None
    hourly_rate: float = 0.0
    active: int = 1


class StaffOut(StaffCreate):
    id: int


# ── Pydantic models (Vendors) ──────────────────────────────────────────

class VendorCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    code: Optional[str] = None
    name: str
    tax_id: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    payment_terms: Optional[str] = None
    acc_key: Optional[int] = None
    active: int = 1


class VendorOut(VendorCreate):
    id: int


# ── Pydantic models (Clients) ──────────────────────────────────────────

class ClientCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    code: Optional[str] = None
    name: Optional[str] = None
    tax_id: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    acc_key: Optional[int] = None


class ClientOut(ClientCreate):
    id: int


# ── Pydantic models (Cost centres) ─────────────────────────────────────

class CostCenterCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    code: str
    name: Optional[str] = None
    type: str = "PRODUCTION"
    parent_id: Optional[int] = None
    budget_limit: float = 0.0


class CostCenterOut(CostCenterCreate):
    id: int


# ── Pydantic models (PNR) ──────────────────────────────────────────────

class PnrCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    pnr_code: str
    client_id: Optional[int] = None
    event_date: Optional[date] = None
    venue: Optional[str] = None
    status: str = "OPEN"
    gross_sales: float = 0.0
    currency: str = "EGP"


class PnrOut(PnrCreate):
    id: int


# ── Dashboard model ────────────────────────────────────────────────────

class ENVDashboard(BaseModel):
    total_clients: int = 0
    total_vendors: int = 0
    total_staff: int = 0
    active_staff: int = 0
    total_cost_centers: int = 0
    total_pnrs: int = 0
    open_pnrs: int = 0
    total_events: int = 0
    open_events: int = 0
    total_sales: float = 0.0
    total_purchases: float = 0.0
    by_event_status: dict = {}


# ── End-points ─────────────────────────────────────────────────────────

@router.get("/staff", response_model=PaginatedResponse[StaffOut])
async def list_staff(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    role: Annotated[Optional[str], Query()] = None,
    department: Annotated[Optional[str], Query()] = None,
    active: Annotated[Optional[int], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(Staff)
    f = []
    if role:
        f.append(Staff.role == role)
    if department:
        f.append(Staff.department == department)
    if active is not None:
        f.append(Staff.active == active)
    if search:
        f.append(or_(
            Staff.name.ilike(f"%{search}%"),
            Staff.code.ilike(f"%{search}%"),
            Staff.email.ilike(f"%{search}%"),
        ))
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Staff.name).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[StaffOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/staff/{staff_id}", response_model=StaffOut)
async def get_staff(
    staff_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    s = (await session.execute(
        select(Staff).where(Staff.id == staff_id)
    )).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Staff not found")
    return StaffOut.model_validate(s)


@router.post("/staff", response_model=StaffOut, status_code=status.HTTP_201_CREATED)
async def create_staff(
    payload: StaffCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    s = Staff(**payload.model_dump(exclude_unset=True))
    session.add(s)
    await session.commit()
    await session.refresh(s)
    return StaffOut.model_validate(s)


@router.get("/clients", response_model=PaginatedResponse[ClientOut])
async def list_clients(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    search: Annotated[Optional[str], Query()] = None,
    acc_key: Annotated[Optional[int], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(Client)
    f = []
    if acc_key is not None:
        f.append(Client.acc_key == acc_key)
    if search:
        f.append(or_(
            Client.name.ilike(f"%{search}%"),
            Client.code.ilike(f"%{search}%"),
            Client.tax_id.ilike(f"%{search}%"),
        ))
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Client.name).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[ClientOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/clients/{client_id}", response_model=ClientOut)
async def get_client(
    client_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    c = (await session.execute(
        select(Client).where(Client.id == client_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Client not found")
    return ClientOut.model_validate(c)


@router.post("/clients", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
async def create_client(
    payload: ClientCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    c = Client(**payload.model_dump(exclude_unset=True))
    session.add(c)
    await session.commit()
    await session.refresh(c)
    return ClientOut.model_validate(c)


@router.get("/vendors", response_model=PaginatedResponse[VendorOut])
async def list_vendors(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    category: Annotated[Optional[str], Query()] = None,
    active: Annotated[Optional[int], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(Vendor)
    f = []
    if category:
        f.append(Vendor.category == category)
    if active is not None:
        f.append(Vendor.active == active)
    if search:
        f.append(or_(
            Vendor.name.ilike(f"%{search}%"),
            Vendor.code.ilike(f"%{search}%"),
            Vendor.tax_id.ilike(f"%{search}%"),
        ))
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Vendor.name).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[VendorOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/vendors/{vendor_id}", response_model=VendorOut)
async def get_vendor(
    vendor_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    v = (await session.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )).scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Vendor not found")
    return VendorOut.model_validate(v)


@router.post("/vendors", response_model=VendorOut, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    payload: VendorCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    v = Vendor(**payload.model_dump(exclude_unset=True))
    session.add(v)
    await session.commit()
    await session.refresh(v)
    return VendorOut.model_validate(v)


@router.get("/cost-centers", response_model=PaginatedResponse[CostCenterOut])
async def list_cost_centers(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    type_: Annotated[Optional[str], Query(alias="type")] = None,
    parent_id: Annotated[Optional[int], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(CostCenter)
    f = []
    if type_:
        f.append(CostCenter.type == type_)
    if parent_id is not None:
        f.append(CostCenter.parent_id == parent_id)
    if search:
        f.append(or_(
            CostCenter.code.ilike(f"%{search}%"),
            CostCenter.name.ilike(f"%{search}%"),
        ))
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(CostCenter.code).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[CostCenterOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/cost-centers/{cc_id}", response_model=CostCenterOut)
async def get_cost_center(
    cc_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    cc = (await session.execute(
        select(CostCenter).where(CostCenter.id == cc_id)
    )).scalar_one_or_none()
    if not cc:
        raise HTTPException(404, "Cost centre not found")
    return CostCenterOut.model_validate(cc)


@router.post("/cost-centers", response_model=CostCenterOut, status_code=status.HTTP_201_CREATED)
async def create_cost_center(
    payload: CostCenterCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    cc = CostCenter(**payload.model_dump(exclude_unset=True))
    session.add(cc)
    await session.commit()
    await session.refresh(cc)
    return CostCenterOut.model_validate(cc)


@router.get("/pnr-dim", response_model=PaginatedResponse[PnrOut])
async def list_pnr(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    client_id: Annotated[Optional[int], Query()] = None,
    status_: Annotated[Optional[str], Query(alias="status")] = None,
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(PnrRecord)
    f = []
    if client_id is not None:
        f.append(PnrRecord.client_id == client_id)
    if status_:
        f.append(PnrRecord.status == status_)
    if date_from:
        f.append(PnrRecord.event_date >= date_from)
    if date_to:
        f.append(PnrRecord.event_date <= date_to)
    if search:
        f.append(or_(
            PnrRecord.pnr_code.ilike(f"%{search}%"),
            PnrRecord.venue.ilike(f"%{search}%"),
        ))
    if f:
        stmt = stmt.where(and_(*f))
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(desc(PnrRecord.event_date), desc(PnrRecord.id))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return PaginatedResponse(
        data=[PnrOut.model_validate(r) for r in rows],
        total=total, page=page, page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/pnr-dim/{pnr_id}", response_model=PnrOut)
async def get_pnr(
    pnr_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    p = (await session.execute(
        select(PnrRecord).where(PnrRecord.id == pnr_id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "PNR not found")
    return PnrOut.model_validate(p)


@router.post("/pnr-dim", response_model=PnrOut, status_code=status.HTTP_201_CREATED)
async def create_pnr(
    payload: PnrCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    p = PnrRecord(**payload.model_dump(exclude_unset=True))
    session.add(p)
    await session.commit()
    await session.refresh(p)
    return PnrOut.model_validate(p)


@router.get("/dashboard", response_model=ENVDashboard)
async def get_dashboard(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    cli = (await session.execute(select(func.count()).select_from(Client))).scalar() or 0
    ven = (await session.execute(select(func.count()).select_from(Vendor))).scalar() or 0
    st_total = (await session.execute(select(func.count()).select_from(Staff))).scalar() or 0
    st_active = (await session.execute(
        select(func.count()).select_from(Staff).where(Staff.active == 1)
    )).scalar() or 0
    cc = (await session.execute(select(func.count()).select_from(CostCenter))).scalar() or 0
    pnr = (await session.execute(select(func.count()).select_from(PnrRecord))).scalar() or 0
    pnr_open = (await session.execute(
        select(func.count()).select_from(PnrRecord).where(PnrRecord.status == "OPEN")
    )).scalar() or 0
    ev = (await session.execute(select(func.count()).select_from(Event))).scalar() or 0
    ev_open = (await session.execute(
        select(func.count()).select_from(Event).where(Event.status == "OPEN")
    )).scalar() or 0
    sales = (await session.execute(
        select(func.coalesce(func.sum(SalesInvoice.total), 0))
    )).scalar() or 0
    pur = (await session.execute(
        select(func.coalesce(func.sum(VendorInvoice.total), 0))
    )).scalar() or 0
    ev_status_rows = (await session.execute(
        select(Event.status, func.count().label("cnt"))
        .group_by(Event.status)
    )).all()
    by_status = {r.status: r.cnt for r in ev_status_rows if r.status}
    return ENVDashboard(
        total_clients=cli,
        total_vendors=ven,
        total_staff=st_total,
        active_staff=st_active,
        total_cost_centers=cc,
        total_pnrs=pnr,
        open_pnrs=pnr_open,
        total_events=ev,
        open_events=ev_open,
        total_sales=round(float(sales), 2),
        total_purchases=round(float(pur), 2),
        by_event_status=by_status,
    )


@router.get("/search", response_model=List[dict])
async def cross_search(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    """Cross-table quick search across clients, vendors, staff, PNR, events."""
    pattern = f"%{q}%"
    out: List[dict] = []
    rows = (await session.execute(
        select(Client).where(or_(
            Client.name.ilike(pattern),
            Client.code.ilike(pattern),
            Client.tax_id.ilike(pattern),
        )).limit(limit)
    )).scalars().all()
    for c in rows:
        out.append({
            "type": "client", "id": c.id, "code": c.code,
            "name": c.name, "extra": c.tax_id or "",
        })
    rows = (await session.execute(
        select(Vendor).where(or_(
            Vendor.name.ilike(pattern),
            Vendor.code.ilike(pattern),
        )).limit(limit)
    )).scalars().all()
    for v in rows:
        out.append({
            "type": "vendor", "id": v.id, "code": v.code,
            "name": v.name, "extra": v.category or "",
        })
    rows = (await session.execute(
        select(Staff).where(or_(
            Staff.name.ilike(pattern),
            Staff.code.ilike(pattern),
        )).limit(limit)
    )).scalars().all()
    for s in rows:
        out.append({
            "type": "staff", "id": s.id, "code": s.code,
            "name": s.name, "extra": s.role or "",
        })
    rows = (await session.execute(
        select(PnrRecord).where(or_(
            PnrRecord.pnr_code.ilike(pattern),
            PnrRecord.venue.ilike(pattern),
        )).limit(limit)
    )).scalars().all()
    for p in rows:
        out.append({
            "type": "pnr", "id": p.id, "code": p.pnr_code,
            "name": p.venue or "", "extra": p.status or "",
        })
    rows = (await session.execute(
        select(Event).where(or_(
            Event.event_code.ilike(pattern),
            Event.event_name.ilike(pattern),
            Event.venue.ilike(pattern),
        )).limit(limit)
    )).scalars().all()
    for e in rows:
        out.append({
            "type": "event", "id": e.id, "code": e.event_code,
            "name": e.event_name or "", "extra": e.status or "",
        })
    return out
