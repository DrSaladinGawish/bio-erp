from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.models.manufacturing import Bioreactor, CellLine, GeneConstruct, RawMaterial

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/manufacturing", tags=["manufacturing"])


# ── Pydantic schemas ─────────────────────────────────────────────

class BioreactorCreate(BaseModel):
    reactor_code: str
    name: str
    reactor_type: str = "stirred_tank"
    working_volume_l: float = 0
    max_volume_l: Optional[float] = None
    temperature_range: Optional[str] = None
    ph_range: Optional[str] = None
    agitation_rpm: Optional[int] = None
    aeration_rate_vvm: Optional[float] = None
    status: str = "available"

class BioreactorUpdate(BaseModel):
    reactor_code: Optional[str] = None
    name: Optional[str] = None
    reactor_type: Optional[str] = None
    working_volume_l: Optional[float] = None
    max_volume_l: Optional[float] = None
    temperature_range: Optional[str] = None
    ph_range: Optional[str] = None
    agitation_rpm: Optional[int] = None
    aeration_rate_vvm: Optional[float] = None
    status: Optional[str] = None

class CellLineCreate(BaseModel):
    cell_code: str
    name: str
    organism: Optional[str] = None
    cell_type: str = "CHO"
    doubling_time_hr: Optional[float] = None
    max_density_cells_per_ml: Optional[float] = None
    viability_threshold: float = 80.0
    atp_maintenance_cost: float = 0

class CellLineUpdate(BaseModel):
    cell_code: Optional[str] = None
    name: Optional[str] = None
    organism: Optional[str] = None
    cell_type: Optional[str] = None
    doubling_time_hr: Optional[float] = None
    max_density_cells_per_ml: Optional[float] = None
    viability_threshold: Optional[float] = None
    atp_maintenance_cost: Optional[float] = None

class GeneConstructCreate(BaseModel):
    construct_code: str
    name: str
    plasmid_size_kb: Optional[float] = None
    copy_number: int = 50
    induction_method: str = "iptg"
    promoter: Optional[str] = None
    resistance_marker: Optional[str] = None
    construction_cost_egp: float = 0

class GeneConstructUpdate(BaseModel):
    construct_code: Optional[str] = None
    name: Optional[str] = None
    plasmid_size_kb: Optional[float] = None
    copy_number: Optional[int] = None
    induction_method: Optional[str] = None
    promoter: Optional[str] = None
    resistance_marker: Optional[str] = None
    construction_cost_egp: Optional[float] = None

class RawMaterialCreate(BaseModel):
    material_code: str
    name: str
    material_type: str = "substrate"
    unit_cost_egp: float = 0
    atp_per_mol: float = 0
    density_g_per_l: Optional[float] = None

class RawMaterialUpdate(BaseModel):
    material_code: Optional[str] = None
    name: Optional[str] = None
    material_type: Optional[str] = None
    unit_cost_egp: Optional[float] = None
    atp_per_mol: Optional[float] = None
    density_g_per_l: Optional[float] = None


# ── Helpers ──────────────────────────────────────────────────────

def _serialize(obj):
    d = {}
    for c in obj.__table__.columns.keys():
        val = getattr(obj, c, None)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        if isinstance(val, float):
            val = round(val, 6)
        d[c] = val
    return d


async def _paginated_list(model, db, page, page_size, search=None, name_field="name"):
    query = select(model).where(model.deleted_at.is_(None))
    if search and hasattr(model, name_field):
        query = query.where(getattr(model, name_field).ilike(f"%{search}%"))
    query = query.order_by(model.created_at.desc())
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    return {
        "data": [_serialize(i) for i in result.scalars().all()],
        "total": total, "page": page, "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size else 0,
    }


async def _get_or_404(model, entity_id, db):
    result = await db.execute(select(model).where(model.id == entity_id, model.deleted_at.is_(None)))
    obj = result.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{model.__name__} not found")
    return obj


async def _create_entity(model, payload, db):
    obj = model(**payload.model_dump())
    db.add(obj)
    try:
        await db.commit()
        await db.refresh(obj)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return obj


async def _update_entity(obj, payload, db):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    try:
        await db.commit()
        await db.refresh(obj)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return obj


async def _delete_entity(obj, db):
    obj.deleted_at = datetime.now(timezone.utc)
    obj.is_active = False
    await db.commit()


# ═══════════════════════════════════════════════════════════════════
#  BIOREACTORS
# ═══════════════════════════════════════════════════════════════════

@router.get("/bioreactors")
async def list_bioreactors(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await _paginated_list(Bioreactor, db, page, page_size, search)

@router.get("/bioreactors/{entity_id}")
async def get_bioreactor(
    entity_id: int,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return _serialize(await _get_or_404(Bioreactor, entity_id, db))

@router.post("/bioreactors", status_code=status.HTTP_201_CREATED)
async def create_bioreactor(
    payload: BioreactorCreate,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return _serialize(await _create_entity(Bioreactor, payload, db))

@router.put("/bioreactors/{entity_id}")
async def update_bioreactor(
    entity_id: int, payload: BioreactorUpdate,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    obj = await _get_or_404(Bioreactor, entity_id, db)
    return _serialize(await _update_entity(obj, payload, db))

@router.delete("/bioreactors/{entity_id}")
async def delete_bioreactor(
    entity_id: int,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    obj = await _get_or_404(Bioreactor, entity_id, db)
    await _delete_entity(obj, db)
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════════════
#  CELL LINES
# ═══════════════════════════════════════════════════════════════════

@router.get("/cell-lines")
async def list_cell_lines(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await _paginated_list(CellLine, db, page, page_size, search)

@router.get("/cell-lines/{entity_id}")
async def get_cell_line(
    entity_id: int,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return _serialize(await _get_or_404(CellLine, entity_id, db))

@router.post("/cell-lines", status_code=status.HTTP_201_CREATED)
async def create_cell_line(
    payload: CellLineCreate,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return _serialize(await _create_entity(CellLine, payload, db))

@router.put("/cell-lines/{entity_id}")
async def update_cell_line(
    entity_id: int, payload: CellLineUpdate,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    obj = await _get_or_404(CellLine, entity_id, db)
    return _serialize(await _update_entity(obj, payload, db))

@router.delete("/cell-lines/{entity_id}")
async def delete_cell_line(
    entity_id: int,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    obj = await _get_or_404(CellLine, entity_id, db)
    await _delete_entity(obj, db)
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════════════
#  GENE CONSTRUCTS
# ═══════════════════════════════════════════════════════════════════

@router.get("/gene-constructs")
async def list_gene_constructs(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await _paginated_list(GeneConstruct, db, page, page_size, search)

@router.get("/gene-constructs/{entity_id}")
async def get_gene_construct(
    entity_id: int,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return _serialize(await _get_or_404(GeneConstruct, entity_id, db))

@router.post("/gene-constructs", status_code=status.HTTP_201_CREATED)
async def create_gene_construct(
    payload: GeneConstructCreate,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return _serialize(await _create_entity(GeneConstruct, payload, db))

@router.put("/gene-constructs/{entity_id}")
async def update_gene_construct(
    entity_id: int, payload: GeneConstructUpdate,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    obj = await _get_or_404(GeneConstruct, entity_id, db)
    return _serialize(await _update_entity(obj, payload, db))

@router.delete("/gene-constructs/{entity_id}")
async def delete_gene_construct(
    entity_id: int,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    obj = await _get_or_404(GeneConstruct, entity_id, db)
    await _delete_entity(obj, db)
    return {"deleted": True}


# ═══════════════════════════════════════════════════════════════════
#  RAW MATERIALS
# ═══════════════════════════════════════════════════════════════════

@router.get("/raw-materials")
async def list_raw_materials(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return await _paginated_list(RawMaterial, db, page, page_size, search)

@router.get("/raw-materials/{entity_id}")
async def get_raw_material(
    entity_id: int,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return _serialize(await _get_or_404(RawMaterial, entity_id, db))

@router.post("/raw-materials", status_code=status.HTTP_201_CREATED)
async def create_raw_material(
    payload: RawMaterialCreate,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    return _serialize(await _create_entity(RawMaterial, payload, db))

@router.put("/raw-materials/{entity_id}")
async def update_raw_material(
    entity_id: int, payload: RawMaterialUpdate,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    obj = await _get_or_404(RawMaterial, entity_id, db)
    return _serialize(await _update_entity(obj, payload, db))

@router.delete("/raw-materials/{entity_id}")
async def delete_raw_material(
    entity_id: int,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    obj = await _get_or_404(RawMaterial, entity_id, db)
    await _delete_entity(obj, db)
    return {"deleted": True}
