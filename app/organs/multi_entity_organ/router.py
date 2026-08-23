"""
Multi-Entity Consolidation Router
==================================
Endpoints for:
  - Entity & ownership management
  - Intercompany transactions & balance matching
  - Consolidation periods & runs
  - Elimination entries
  - Currency translation rates
  - Consolidated reports
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.organs.multi_entity_organ.schemas import (
    EntityCreate, EntityResponse,
    OwnershipCreate, OwnershipResponse,
    ICTransactionCreate, ICTransactionResponse,
    PeriodCreate, PeriodResponse,
    ConsolidationRunCreate, ConsolidationRunResponse,
    EliminationEntryCreate, EliminationEntryResponse,
    TranslationRateCreate, TranslationRateResponse,
    ReportResponse, ConsolidationRunDetail,
)
from app.organs.multi_entity_organ.service import ConsolidationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["multi-entity"])

svc = ConsolidationService()


# ── Entity Endpoints ────────────────────────────────────────────────────


@router.post("/entities", response_model=EntityResponse, status_code=201)
async def create_entity(data: EntityCreate, db: AsyncSession = Depends(get_db)):
    entity = await svc.create_entity(db, data.model_dump())
    return EntityResponse(
        id=entity.id,
        code=entity.code,
        name_en=entity.name_en,
        name_ar=entity.name_ar,
        entity_type=entity.entity_type.value,
        country=entity.country,
        currency_id=entity.currency_id,
        consolidation_method=entity.consolidation_method.value,
        is_consolidating_entity=entity.is_consolidating_entity,
        is_active=entity.is_active,
        created_at=entity.created_at,
    )


@router.get("/entities", response_model=List[EntityResponse])
async def list_entities(
    entity_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    entities = await svc.get_entities(db, entity_type)
    return [
        EntityResponse(
            id=e.id, code=e.code, name_en=e.name_en, name_ar=e.name_ar,
            entity_type=e.entity_type.value, country=e.country,
            currency_id=e.currency_id,
            consolidation_method=e.consolidation_method.value,
            is_consolidating_entity=e.is_consolidating_entity,
            is_active=e.is_active, created_at=e.created_at,
        )
        for e in entities
    ]


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: int, db: AsyncSession = Depends(get_db)):
    entity = await svc.get_entity(db, entity_id)
    if not entity:
        raise HTTPException(404, "Entity not found")
    return EntityResponse(
        id=entity.id, code=entity.code, name_en=entity.name_en,
        name_ar=entity.name_ar,
        entity_type=entity.entity_type.value, country=entity.country,
        currency_id=entity.currency_id,
        consolidation_method=entity.consolidation_method.value,
        is_consolidating_entity=entity.is_consolidating_entity,
        is_active=entity.is_active, created_at=entity.created_at,
    )


@router.get("/group-structure")
async def group_structure(
    root_entity_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_group_structure(db, root_entity_id)


# ── Ownership Endpoints ────────────────────────────────────────────────


@router.post("/ownerships", response_model=OwnershipResponse, status_code=201)
async def create_ownership(data: OwnershipCreate, db: AsyncSession = Depends(get_db)):
    own = await svc.create_ownership(db, data.model_dump())
    return OwnershipResponse(
        id=own.id,
        parent_entity_id=own.parent_entity_id,
        subsidiary_entity_id=own.subsidiary_entity_id,
        ownership_pct=own.ownership_pct,
        effective_date=own.effective_date,
        disposal_date=own.disposal_date,
        is_direct=own.is_direct,
    )


@router.get("/ownerships/effective/{entity_id}")
async def effective_ownership(
    entity_id: int, db: AsyncSession = Depends(get_db)
):
    pct = await svc.calculate_effective_ownership(db, entity_id)
    return {"entity_id": entity_id, "effective_ownership_pct": pct}


# ── Intercompany Endpoints ──────────────────────────────────────────────


@router.post("/ic-transactions", response_model=ICTransactionResponse, status_code=201)
async def create_ic_transaction(
    data: ICTransactionCreate, db: AsyncSession = Depends(get_db)
):
    txn = await svc.create_ic_transaction(db, data.model_dump())
    return ICTransactionResponse(
        id=txn.id,
        transaction_number=txn.transaction_number,
        transaction_date=txn.transaction_date,
        from_entity_id=txn.from_entity_id,
        to_entity_id=txn.to_entity_id,
        transaction_type=txn.transaction_type,
        amount=txn.amount,
        currency_id=txn.currency_id,
        elimination_status=txn.elimination_status,
        created_at=txn.created_at,
    )


@router.get("/ic-transactions", response_model=List[ICTransactionResponse])
async def list_ic_transactions(
    from_entity_id: Optional[int] = Query(None),
    to_entity_id: Optional[int] = Query(None),
    period_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    txns = await svc.get_ic_transactions(db, from_entity_id, to_entity_id, period_id)
    return [
        ICTransactionResponse(
            id=t.id, transaction_number=t.transaction_number,
            transaction_date=t.transaction_date,
            from_entity_id=t.from_entity_id, to_entity_id=t.to_entity_id,
            transaction_type=t.transaction_type, amount=t.amount,
            currency_id=t.currency_id,
            elimination_status=t.elimination_status, created_at=t.created_at,
        )
        for t in txns
    ]


# ── Period Endpoints ────────────────────────────────────────────────────


@router.post("/periods", response_model=PeriodResponse, status_code=201)
async def create_period(data: PeriodCreate, db: AsyncSession = Depends(get_db)):
    period = await svc.create_period(db, data.model_dump())
    return PeriodResponse(
        id=period.id, name=period.name,
        fiscal_year=period.fiscal_year, period_number=period.period_number,
        start_date=period.start_date, end_date=period.end_date,
        is_closed=period.is_closed,
    )


@router.get("/periods", response_model=List[PeriodResponse])
async def list_periods(db: AsyncSession = Depends(get_db)):
    periods = await svc.get_open_periods(db)
    return [
        PeriodResponse(
            id=p.id, name=p.name,
            fiscal_year=p.fiscal_year, period_number=p.period_number,
            start_date=p.start_date, end_date=p.end_date, is_closed=p.is_closed,
        )
        for p in periods
    ]


@router.get("/periods/{period_id}", response_model=PeriodResponse)
async def get_period(period_id: int, db: AsyncSession = Depends(get_db)):
    period = await svc.get_period(db, period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    return PeriodResponse(
        id=period.id, name=period.name,
        fiscal_year=period.fiscal_year, period_number=period.period_number,
        start_date=period.start_date, end_date=period.end_date,
        is_closed=period.is_closed,
    )


# ── Consolidation Run Endpoints ─────────────────────────────────────────


@router.post("/consolidations", response_model=ConsolidationRunResponse, status_code=201)
async def start_consolidation(
    data: ConsolidationRunCreate, db: AsyncSession = Depends(get_db)
):
    run = await svc.start_consolidation(db, data.model_dump())
    return ConsolidationRunResponse(
        id=run.id, period_id=run.period_id,
        consolidating_entity_id=run.consolidating_entity_id,
        run_number=run.run_number,
        status=run.status.value,
        started_at=run.started_at, completed_at=run.completed_at,
        created_at=run.created_at,
    )


@router.post("/consolidations/{run_id}/execute")
async def execute_consolidation(
    run_id: int, db: AsyncSession = Depends(get_db)
):
    try:
        run = await svc.run_full_consolidation(db, run_id)
        return {
            "success": True,
            "run_id": run.id,
            "status": run.status.value,
            "completed_at": run.completed_at,
            "summary": run.result_summary,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/consolidations", response_model=List[ConsolidationRunResponse])
async def list_consolidations(
    period_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    runs = await svc.get_runs(db, period_id)
    return [
        ConsolidationRunResponse(
            id=r.id, period_id=r.period_id,
            consolidating_entity_id=r.consolidating_entity_id,
            run_number=r.run_number,
            status=r.status.value,
            started_at=r.started_at, completed_at=r.completed_at,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/consolidations/{run_id}")
async def get_consolidation_detail(
    run_id: int, db: AsyncSession = Depends(get_db)
):
    detail = await svc.get_run_detail(db, run_id)
    if not detail:
        raise HTTPException(404, "Consolidation run not found")
    return detail


@router.post("/consolidations/{run_id}/approve")
async def approve_consolidation(
    run_id: int, user_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        run = await svc.approve_run(db, run_id, user_id)
        return {
            "success": True,
            "run_id": run.id,
            "status": run.status.value,
            "approved_at": run.approved_at,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── IC Balance Matching ─────────────────────────────────────────────────


@router.get("/ic-balances/match/{period_id}")
async def match_ic_balances(
    period_id: int, db: AsyncSession = Depends(get_db)
):
    matches = await svc.match_ic_balances(db, period_id)
    return {
        "period_id": period_id,
        "matches": matches,
        "unmatched_count": sum(1 for m in matches if not m["matched"]),
    }


# ── Currency Translation Rates ──────────────────────────────────────────


@router.post("/translation-rates", response_model=TranslationRateResponse, status_code=201)
async def create_translation_rate(
    data: TranslationRateCreate, db: AsyncSession = Depends(get_db)
):
    rate = await svc.create_translation_rate(db, data.model_dump())
    return TranslationRateResponse(
        id=rate.id,
        from_currency_id=rate.from_currency_id,
        to_currency_id=rate.to_currency_id,
        rate_date=rate.rate_date,
        spot_rate=rate.spot_rate,
        closing_rate=rate.closing_rate,
    )



