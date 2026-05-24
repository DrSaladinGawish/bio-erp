from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.item import ItemCategory, ItemSubCategory, EventMasterNode
from app.services.audit_logger import AuditLogger
from app.services.auto_classification import AutoClassificationEngine

router = APIRouter(prefix="/api/v1/items", tags=["Items / Inventory"])
classifier = AutoClassificationEngine()

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


class CategoryCreate(BaseModel):
    code: str
    name_en: str
    name_ar: str | None = None
    default_markup: float = 0.12


class SubCategoryCreate(BaseModel):
    code: str
    name_en: str
    name_ar: str | None = None
    category_id: int
    classification: str | None = None


class MasterNodeCreate(BaseModel):
    code: str
    name_en: str
    name_ar: str | None = None
    layer: int
    parent_id: int | None = None
    category_id: int | None = None
    sub_category_id: int | None = None
    uom: str | None = None
    default_lead_time: int = 0
    dependency_weight: float = 1.0
    default_cost: float = 0.0
    classification_code: str | None = None


# === CATEGORIES ===


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ItemCategory).where(ItemCategory.is_active).order_by(ItemCategory.code)
    )
    cats = result.scalars().all()
    return [
        {
            "id": c.id,
            "code": c.code,
            "name_en": c.name_en,
            "name_ar": c.name_ar,
            "default_markup": c.default_markup,
            "markup_label": f"{c.default_markup * 100:.0f}%",
        }
        for c in cats
    ]


@router.post("/categories")
async def create_category(
    req: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("admin.access")),
):
    cat = ItemCategory(
        code=req.code.upper(),
        name_en=req.name_en,
        name_ar=req.name_ar,
        default_markup=req.default_markup,
    )
    db.add(cat)
    await db.flush()
    logger = AuditLogger(db)
    await logger.log(
        "CREATE", "ItemCategory", cat.id, new_value=req.model_dump(), actor_id=user.id
    )
    return cat


# === SUB-CATEGORIES ===


@router.get("/sub-categories")
async def list_sub_categories(
    category_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(ItemSubCategory).order_by(ItemSubCategory.code)
    if category_id:
        query = query.where(ItemSubCategory.category_id == category_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/sub-categories")
async def create_sub_category(
    req: SubCategoryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("admin.access")),
):
    sub = ItemSubCategory(
        code=req.code.upper(),
        name_en=req.name_en,
        name_ar=req.name_ar,
        category_id=req.category_id,
        classification=req.classification,
    )
    db.add(sub)
    await db.flush()
    return sub


# === MASTER NODES (505-item catalog) ===


@router.get("/master-nodes")
async def list_master_nodes(
    layer: int | None = Query(None),
    parent_id: int | None = Query(None),
    category_id: int | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(EventMasterNode).where(EventMasterNode.is_active)
    if layer:
        query = query.where(EventMasterNode.layer == layer)
    if parent_id is not None:
        query = query.where(EventMasterNode.parent_id == parent_id)
    elif parent_id is None and layer == 1:
        query = query.where(EventMasterNode.parent_id.is_(None))
    if category_id:
        query = query.where(EventMasterNode.category_id == category_id)
    if search:
        query = query.where(
            or_(
                EventMasterNode.name_en.ilike(f"%{search}%"),
                EventMasterNode.name_ar.ilike(f"%{search}%"),
                EventMasterNode.code.ilike(f"%{search}%"),
            )
        )
    query = query.order_by(EventMasterNode.code)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/master-nodes/tree")
async def get_master_node_tree(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EventMasterNode)
        .where(EventMasterNode.is_active, EventMasterNode.parent_id.is_(None))
        .order_by(EventMasterNode.code)
    )
    roots = result.scalars().all()
    tree = []
    for root in roots:
        children_result = await db.execute(
            select(EventMasterNode)
            .where(
                EventMasterNode.parent_id == root.id,
                EventMasterNode.is_active,
            )
            .order_by(EventMasterNode.code)
        )
        children = children_result.scalars().all()
        tree.append(
            {
                "id": root.id,
                "code": root.code,
                "name_en": root.name_en,
                "name_ar": root.name_ar,
                "layer": root.layer,
                "children": [
                    {
                        "id": c.id,
                        "code": c.code,
                        "name_en": c.name_en,
                        "name_ar": c.name_ar,
                        "layer": c.layer,
                    }
                    for c in children
                ],
            }
        )
    return tree


@router.post("/master-nodes")
async def create_master_node(
    req: MasterNodeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("admin.access")),
):
    node = EventMasterNode(**req.model_dump())
    db.add(node)
    await db.flush()
    logger = AuditLogger(db)
    await logger.log(
        "CREATE",
        "EventMasterNode",
        node.id,
        new_value=req.model_dump(),
        actor_id=user.id,
    )
    return node


@router.get("/master-nodes/{node_id}")
async def get_master_node(node_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EventMasterNode)
        .options(joinedload(EventMasterNode.children))
        .where(EventMasterNode.id == node_id)
    )
    node = result.unique().scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Master node not found")
    return node


# === BOOTH TEMPLATES ===


@router.get("/booth-templates")
async def list_booth_templates():
    return classifier.BOOTH_TEMPLATES


@router.get("/booth-templates/{tier}")
async def get_booth_template(tier: str):
    template = classifier.get_booth_template(tier)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown booth tier: {tier}. Use BASIC, PREMIUM, or VIP.",
        )
    return template


# === AUTO-CLASSIFICATION ===


@router.post("/classify")
async def classify_item(description: str = Query(...)):
    return classifier.classify(description)


@router.get("/suggestions")
async def get_suggestions(q: str = Query(...), limit: int = Query(5)):
    return classifier.get_suggestions(q, limit)


# === MARKUP RULES ===


@router.get("/markup-rules")
async def get_markup_rules():
    return [
        {"category": k, "markup": v, "label": f"{v * 100:.0f}%"}
        for k, v in MARKUP_RULES.items()
    ]


@router.get("/markup-rules/{category_code}")
async def get_markup_rule(category_code: str):
    code = category_code.upper()
    if code not in MARKUP_RULES:
        raise HTTPException(
            status_code=404, detail=f"No markup rule for category: {code}"
        )
    return {
        "category": code,
        "markup": MARKUP_RULES[code],
        "label": f"{MARKUP_RULES[code] * 100:.0f}%",
    }
