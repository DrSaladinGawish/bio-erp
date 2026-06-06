"""
intelligence/router.py
FastAPI router exposing the intelligence layer at /api/v1/intelligence/*.
"""
from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.organs.incentivehouse_organ.db import get_db
from app.organs.incentivehouse_organ.intelligence.audit import (
    audit_event, count_audit, query_audit,
)
from app.organs.incentivehouse_organ.intelligence.health import get_health_report
from app.organs.incentivehouse_organ.intelligence.gap import run_gap_analysis
from app.organs.incentivehouse_organ.intelligence.backup import (
    backup_before_change, list_backups,
)
from app.organs.incentivehouse_organ.intelligence.neural import run_all_predictors
from app.organs.incentivehouse_organ.intelligence.or_solver import run_or_solver
from app.organs.incentivehouse_organ.intelligence.scm import run_scm_analysis

logger = logging.getLogger("incentivehouse_organ.intelligence.router")
router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])


# ---- Health ----
@router.get("/health")
def intelligence_health(db: Session = Depends(get_db)):
    return get_health_report(db)


# ---- Gap ----
@router.get("/gap")
def intelligence_gap(db: Session = Depends(get_db)):
    return run_gap_analysis(db)


# ---- Audit ----
@router.get("/audit")
def intelligence_audit(
    table_name: Optional[str] = None,
    record_id: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    items = query_audit(db, table_name=table_name, record_id=record_id,
                        action=action, user_id=user_id, limit=limit)
    return {"count": len(items), "total_audit_records": count_audit(db), "items": items}


class AuditEventIn(BaseModel):
    table_name: str
    record_id: Optional[str] = None
    action: str
    old_value: Optional[dict] = None
    new_value: Optional[dict] = None
    user_id: str = "system"
    extra: Optional[dict] = None


@router.post("/audit")
def intelligence_audit_post(payload: AuditEventIn, db: Session = Depends(get_db)):
    new_id = audit_event(
        db, payload.table_name, payload.record_id, payload.action,
        payload.old_value, payload.new_value, payload.user_id,
        extra=payload.extra,
    )
    return {"id": new_id, "status": "ok" if new_id > 0 else "error"}


# ---- Backup ----
@router.get("/backup")
def intelligence_backup_list():
    return {"backups": list_backups()}


class BackupIn(BaseModel):
    reason: str
    user_id: str = "system"


@router.post("/backup")
def intelligence_backup_run(payload: BackupIn, db: Session = Depends(get_db)):
    return backup_before_change(db, reason=payload.reason, user_id=payload.user_id)


# ---- Neural ----
@router.get("/neural/predict")
def intelligence_neural_predict(db: Session = Depends(get_db)):
    return run_all_predictors(db)


@router.get("/neural/cashflow")
def intelligence_neural_cashflow(horizon: int = 7, db: Session = Depends(get_db)):
    from app.organs.incentivehouse_organ.intelligence.neural import predict_cashflow
    return predict_cashflow(db, horizon)


@router.get("/neural/revenue")
def intelligence_neural_revenue(horizon: int = 7, db: Session = Depends(get_db)):
    from app.organs.incentivehouse_organ.intelligence.neural import predict_revenue
    return predict_revenue(db, horizon)


@router.get("/neural/anomalies")
def intelligence_neural_anomalies(db: Session = Depends(get_db)):
    from app.organs.incentivehouse_organ.intelligence.neural import detect_anomalies
    return detect_anomalies(db)


# ---- OR ----
@router.get("/or/solve")
def intelligence_or_solve(
    engine: str = "all",
    db: Session = Depends(get_db),
):
    return run_or_solver(db, engine=engine)


# ---- SCM ----
@router.get("/scm/analyze")
def intelligence_scm_analyze(
    cell: str = "all",
    db: Session = Depends(get_db),
):
    return run_scm_analysis(db, cell=cell)
