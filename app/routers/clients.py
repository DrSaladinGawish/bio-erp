from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, field_validator
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.client import Client
from app.models.event import Event
from app.services.audit_logger import AuditLogger
from app.services.serial_number import SerialNumberService

router = APIRouter(prefix="/api/v1/clients", tags=["Clients"])


class ClientCreate(BaseModel):
    name_en: str
    name_ar: str | None = None
    tax_id: str | None = None
    commercial_registration: str | None = None
    email: str | None = None
    phone1: str | None = None
    phone2: str | None = None
    address_en: str | None = None
    address_ar: str | None = None
    credit_limit: float = 0.0
    acc_key: int | None = None
    notes: str | None = None
    branch_id: int = 1

    @field_validator("tax_id")
    @classmethod
    def validate_tax_id(cls, v):
        if v and (not v.isdigit() or len(v) not in (9, 14)):
            raise ValueError("Tax ID must be 9 or 14 digits")
        return v


class ClientUpdate(BaseModel):
    name_en: str | None = None
    name_ar: str | None = None
    tax_id: str | None = None
    email: str | None = None
    phone1: str | None = None
    phone2: str | None = None
    address_en: str | None = None
    address_ar: str | None = None
    credit_limit: float | None = None
    notes: str | None = None


@router.get("")
async def list_clients(
    search: str | None = Query(None),
    branch_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("client.read")),
):
    query = select(Client).where(Client.is_active)
    if branch_id:
        query = query.where(Client.branch_id == branch_id)
    if search:
        query = query.where(
            or_(
                Client.name_en.ilike(f"%{search}%"),
                Client.name_ar.ilike(f"%{search}%"),
                Client.tax_id.ilike(f"%{search}%"),
                Client.code.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(Client.name_en)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{client_id}")
async def get_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("client.read")),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/")
async def create_client(
    req: ClientCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("client.create")),
):
    svc = SerialNumberService(db)
    existing = await db.execute(select(Client).where(Client.name_en == req.name_en))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Client with this name already exists"
        )

    code = await svc.generate("CLNT", Client, 4)
    client = Client(
        code=code,
        **req.model_dump(exclude={"acc_key"}),
        acc_key=req.acc_key,
    )
    db.add(client)
    await db.flush()
    logger = AuditLogger(db)
    await logger.log(
        "CREATE", "Client", client.id, new_value=req.model_dump(), actor_id=user.id
    )
    return client


@router.put("/{client_id}")
async def update_client(
    client_id: int,
    req: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("client.update")),
):
    result = await db.execute(select(Client).where(Client.id == client_id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    old = {c.name: getattr(client, c.name) for c in Client.__table__.columns}
    update_data = req.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(client, key, value)

    logger = AuditLogger(db)
    await logger.log(
        "UPDATE",
        "Client",
        client_id,
        old_value=old,
        new_value=update_data,
        actor_id=user.id,
    )
    return {
        "id": client.id,
        "name_en": client.name_en,
        "name_ar": client.name_ar,
        "email": client.email,
        "phone1": client.phone1,
        "is_active": client.is_active,
    }


@router.get("/{client_id}/events")
async def get_client_events(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.read")),
):
    result = await db.execute(
        select(Event)
        .where(Event.client_id == client_id)
        .order_by(Event.created_at.desc())
    )
    return result.scalars().all()
