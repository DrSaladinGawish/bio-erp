from datetime import datetime
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from pydantic import BaseModel, field_validator
from app.database import get_db
from app.middleware.auth import get_current_user, RequirePermission
from app.models.auth import User
from app.models.event import Event, EventBudgetLine
from app.models.item import EventMasterNode
from app.services.audit_logger import AuditLogger
from app.services.markup_engine import MarkupEngine

router = APIRouter(prefix="/api/v1/budget", tags=["Budget"])

MARKUP_RULES = {
    "VEN": 0.12,
    "AV": 0.12,
    "CAT": 0.18,
    "DEC": 0.20,
    "TRN": 0.15,
    "STF": 0.10,
    "MRK": 0.25,
    "MISC": 0.12,
}

VALID_VERSIONS = [1, 2, 3]
BUDGET_SECTIONS = ["BOOTH", "EQUIPMENT", "FURNITURE", "STAFFING", "GIVEAWAYS"]


class BudgetLineCreate(BaseModel):
    master_node_id: int | None = None
    description: str
    quantity: int = 1
    unit_cost: float = 0.0
    markup_percent: float | None = None
    section: str | None = None
    budget_version: int = 1
    revision_reason: str | None = None

    @field_validator("budget_version")
    @classmethod
    def validate_version(cls, v):
        if v not in VALID_VERSIONS:
            raise ValueError(
                f"Budget version must be one of V1/V2/V3 ({VALID_VERSIONS})"
            )
        return v

    @field_validator("section")
    @classmethod
    def validate_section(cls, v):
        if v and v.upper() not in BUDGET_SECTIONS:
            raise ValueError(f"Section must be one of: {', '.join(BUDGET_SECTIONS)}")
        return v.upper() if v else v


class BudgetLineItemPayload(BaseModel):
    master_node_id: int | None = None
    description: str
    quantity: int = 1
    unit_cost: float = 0.0
    markup_pct: float | None = None
    section: str | None = None
    currency_id: int = 1


class BudgetRevisionCreate(BaseModel):
    reason: str | None = None
    line_items: list[BudgetLineItemPayload] = []


@router.get("/markup-rules")
async def get_markup_rules():
    return [
        {"category": k, "markup": v, "label": f"{v * 100:.0f}%"}
        for k, v in MARKUP_RULES.items()
    ]


@router.get("/rules/{category_code}")
async def get_markup_rule(category_code: str):
    code = category_code.upper()
    if code not in MARKUP_RULES:
        raise HTTPException(status_code=404, detail=f"No rule for {code}")
    return {"category": code, "markup": MARKUP_RULES[code]}


@router.get("/{event_id}")
async def get_event_budget(
    event_id: int,
    version: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.read")),
):
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    query = select(EventBudgetLine).where(EventBudgetLine.event_id == event_id)
    if version:
        query = query.where(EventBudgetLine.budget_version == version)
    query = query.order_by(
        EventBudgetLine.budget_version, EventBudgetLine.section, EventBudgetLine.id
    )
    result = await db.execute(query)
    lines = result.scalars().all()

    sections = {}
    totals = {"total_cost": 0, "total_selling": 0, "total_markup": 0, "profit": 0}

    for line in lines:
        sec = line.section or "UNCATEGORIZED"
        if sec not in sections:
            sections[sec] = {
                "section": sec,
                "lines": [],
                "subtotal_cost": 0,
                "subtotal_selling": 0,
            }
        sections[sec]["lines"].append(line)
        sections[sec]["subtotal_cost"] += line.total_cost
        sections[sec]["subtotal_selling"] += line.selling_price
        totals["total_cost"] += line.total_cost
        totals["total_selling"] += line.selling_price

    totals["total_markup"] = round(totals["total_selling"] - totals["total_cost"], 2)
    totals["profit"] = round(totals["total_markup"], 2)
    totals["margin"] = (
        round((totals["profit"] / totals["total_selling"] * 100), 2)
        if totals["total_selling"]
        else 0
    )

    return {
        "event_id": event_id,
        "event_code": event.event_code,
        "current_version": event.budget_version,
        "sections": list(sections.values()),
        "totals": {
            k: round(v, 2) if isinstance(v, float) else v for k, v in totals.items()
        },
    }


@router.post("/{event_id}/lines")
async def add_budget_line(
    event_id: int,
    req: BudgetLineCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.update")),
):
    event_result = await db.execute(select(Event).where(Event.id == event_id))
    event = event_result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    markup = req.markup_percent
    if not markup:
        cat_code = "MISC"
        if req.master_node_id:
            node_result = await db.execute(
                select(EventMasterNode).where(EventMasterNode.id == req.master_node_id)
            )
            node = node_result.scalar_one_or_none()
            if node and node.category:
                cat_code = node.category.code
        markup = MarkupEngine().get_markup(cat_code)

    total_cost = req.quantity * req.unit_cost
    selling_price = total_cost * (1 + markup)

    line = EventBudgetLine(
        event_id=event_id,
        total_cost=round(total_cost, 2),
        selling_price=round(selling_price, 2),
        markup_percent=markup,
        **req.model_dump(exclude={"markup_percent"}),
    )
    db.add(line)
    await db.flush()

    logger = AuditLogger(db)
    await logger.log(
        "CREATE",
        "EventBudgetLine",
        line.id,
        new_value={
            **req.model_dump(),
            "total_cost": total_cost,
            "selling_price": selling_price,
        },
        actor_id=user.id,
    )
    return line


@router.delete("/{event_id}/lines/{line_id}")
async def delete_budget_line(
    event_id: int,
    line_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.update")),
):
    result = await db.execute(
        select(EventBudgetLine).where(
            EventBudgetLine.id == line_id,
            EventBudgetLine.event_id == event_id,
        )
    )
    line = result.scalar_one_or_none()
    if not line:
        raise HTTPException(status_code=404, detail="Budget line not found")
    await db.delete(line)
    return {"deleted": line_id}


@router.post("/{event_id}/revise", response_model=dict)
async def revise_budget(
    event_id: int,
    revision: BudgetRevisionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EventBudgetLine)
        .where(EventBudgetLine.event_id == event_id)
        .options(joinedload(EventBudgetLine.event))
    )
    existing = result.scalars().all()

    if not existing:
        raise HTTPException(status_code=404, detail="No budget found for this event")

    for line in existing:
        line.is_active = False
        line.archived_at = datetime.now(timezone.utc).replace(tzinfo=None)

    new_lines = []
    total = 0.0
    for item in revision.line_items:
        markup = item.markup_pct or 0
        total_cost = (item.quantity * item.unit_cost) * (1 + markup / 100)
        line = EventBudgetLine(
            event_id=event_id,
            master_node_id=item.master_node_id,
            description=item.description,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            markup_percent=markup,
            total_cost=round(total_cost, 2),
            selling_price=round(total_cost, 2),
            budget_version=(existing[0].budget_version + 1)
            if existing[0].budget_version
            else 1,
            is_active=True,
            section=item.section,
            currency_id=item.currency_id,
            revision_reason=revision.reason,
        )
        db.add(line)
        new_lines.append(line)
        total += line.total_cost

    await db.commit()

    result = await db.execute(
        select(EventBudgetLine)
        .where(EventBudgetLine.event_id == event_id)
        .where(EventBudgetLine.is_active)
        .options(
            joinedload(EventBudgetLine.currency),
        )
    )
    refreshed = result.scalars().all()

    return {
        "event_id": event_id,
        "version": refreshed[0].budget_version if refreshed else 1,
        "total_budget": round(total, 2),
        "line_count": len(refreshed),
        "lines": [
            {
                "id": line.id,
                "description": line.description,
                "quantity": line.quantity,
                "unit_cost": float(line.unit_cost) if line.unit_cost else 0,
                "markup_pct": line.markup_percent,
                "total_cost": float(line.total_cost) if line.total_cost else 0,
                "section": line.section,
                "currency": line.currency.code if line.currency else "EGP",
            }
            for line in refreshed
        ],
        "revised_by": user.username,
        "revised_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }


@router.get("/{event_id}/versions")
async def get_budget_versions(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("event.read")),
):
    result = await db.execute(
        select(
            EventBudgetLine.budget_version,
            func.count(EventBudgetLine.id),
            func.sum(EventBudgetLine.total_cost),
            func.sum(EventBudgetLine.selling_price),
        )
        .where(EventBudgetLine.event_id == event_id)
        .group_by(EventBudgetLine.budget_version)
        .order_by(EventBudgetLine.budget_version)
    )
    versions = []
    for row in result.all():
        versions.append(
            {
                "version": f"V{row.budget_version}",
                "line_count": row[1],
                "total_cost": round(row[2] or 0, 2),
                "total_selling": round(row[3] or 0, 2),
                "profit": round((row[3] or 0) - (row[2] or 0), 2),
            }
        )
    return versions
