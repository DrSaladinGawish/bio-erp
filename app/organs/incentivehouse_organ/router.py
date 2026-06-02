"""
IncentiveHouse ERP Router — Staging review, promote, audit endpoints.
All writes go to staging tables only; production requires explicit --migrate.
"""
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.organs.incentivehouse_organ.schemas import (
    PromoteRequest, PromoteResponse,
    StagingListResponse, StagingQuery, StagingRecord,
)
from app.organs.incentivehouse_organ.models import (
    STAGING_TABLE_NAMES, PRODUCTION_TABLE_NAMES,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/incentivehouse", tags=["incentivehouse"])


def get_sync_db():
    from app.database import get_sync_session
    session = get_sync_session()
    try:
        yield session
    finally:
        session.close()


# ── Staging Query / Review ──

@router.post("/staging/query", response_model=StagingListResponse)
def query_staging(q: StagingQuery, db: Session = Depends(get_sync_db)):
    """Query staged records by module and validation status."""
    modules = ["Bnk", "Sal", "Pur", "Evn", "Env"] if q.module == "all" else [q.module]
    all_records = []
    total = 0

    for mod in modules:
        table = STAGING_TABLE_NAMES[mod]
        where = ""
        params: dict = {}
        if q.status:
            where = "AND validation_status = :status"
            params["status"] = q.status

        try:
            count = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE 1=1 {where}"),
                params,
            ).scalar()
            total += count

            rows = db.execute(
                text(f"""
                    SELECT id, transaction_id, transaction_date, account_code,
                           description, debit_amount, credit_amount, currency,
                           sub_led_code, pnr_id, client_id, validation_status,
                           validation_errors, staged_at
                    FROM {table}
                    WHERE 1=1 {where}
                    ORDER BY id DESC
                    LIMIT :limit OFFSET :offset
                """),
                {**params, "limit": q.limit, "offset": q.offset},
            ).fetchall()

            for r in rows:
                val_errors = []
                try:
                    val_errors = json.loads(r.validation_errors or "[]")
                except (json.JSONDecodeError, TypeError):
                    pass
                all_records.append(StagingRecord(
                    id=r.id,
                    transaction_id=r.transaction_id or "",
                    transaction_date=str(r.transaction_date or ""),
                    account_code=str(r.account_code or ""),
                    description=str(r.description or ""),
                    debit_amount=float(r.debit_amount or 0),
                    credit_amount=float(r.credit_amount or 0),
                    currency=str(r.currency or "EGP"),
                    sub_led_code=int(r.sub_led_code or 0),
                    pnr_id=int(r.pnr_id or 0),
                    client_id=int(r.client_id or 0),
                    validation_status=str(r.validation_status or "PASS"),
                    validation_errors=val_errors,
                    staged_at=str(r.staged_at or ""),
                ))
        except Exception as exc:
            logger.warning("Query failed for %s: %s", table, exc)

    return StagingListResponse(module=q.module, total=total, records=all_records[:q.limit])


@router.get("/staging/summary")
def staging_summary(db: Session = Depends(get_sync_db)):
    """Summary counts across all staging tables."""
    summary = {}
    for mod, table in STAGING_TABLE_NAMES.items():
        try:
            total = db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            passed = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE validation_status = 'PASS'")
            ).scalar()
            warned = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE validation_status = 'WARN'")
            ).scalar()
            failed = db.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE validation_status = 'FAIL'")
            ).scalar()
            summary[mod] = {
                "table": table,
                "total": total,
                "pass": passed,
                "warn": warned,
                "fail": failed,
            }
        except Exception as exc:
            summary[mod] = {"error": str(exc)}
    return {"timestamp": datetime.now().isoformat(), "modules": summary}


# ── Promote to Production ──

@router.post("/promote", response_model=PromoteResponse)
def promote_to_production(
    req: PromoteRequest,
    db: Session = Depends(get_sync_db),
):
    """
    Promote validated staging records to production ledger tables.
    Requires confirmed=True to execute — default is dry-run (shows what would happen).
    """
    if req.module not in STAGING_TABLE_NAMES:
        raise HTTPException(400, f"Invalid module: {req.module}")

    staging_table = STAGING_TABLE_NAMES[req.module]
    prod_table = PRODUCTION_TABLE_NAMES[req.module]

    if req.record_ids:
        id_list = ",".join(str(i) for i in req.record_ids)
        where = f"WHERE id IN ({id_list}) AND validation_status IN ('PASS','WARN')"
        requested = len(req.record_ids)
    else:
        where = "WHERE validation_status IN ('PASS','WARN')"
        requested = db.execute(
            text(f"SELECT COUNT(*) FROM {staging_table} {where}")
        ).scalar()

    if not req.confirmed:
        return PromoteResponse(
            module=req.module,
            requested=requested,
            promoted=0,
            table_from=staging_table,
            table_to=prod_table,
            confirmation_required=True,
            message=f"Dry-run: {requested} records ready to promote to {prod_table}. "
                    f"Set confirmed=True to execute.",
        )

    # Promote: insert validated rows not already in production
    promoted = db.execute(
        text(f"""
            INSERT INTO {prod_table}
            (transaction_id, transaction_date, account_code, description,
             debit_amount, credit_amount, currency, exchange_rate,
             sub_led_code, pnr_id, client_id, cost_center,
             validation_status, validation_errors, source_file, source_row,
             promoted_at, promoted_by)
            SELECT
                transaction_id, transaction_date, account_code, description,
                debit_amount, credit_amount, currency, exchange_rate,
                sub_led_code, pnr_id, client_id, cost_center,
                validation_status, validation_errors, source_file, source_row,
                :now, :user
            FROM {staging_table} s
            WHERE s.validation_status IN ('PASS','WARN')
            AND NOT EXISTS (
                SELECT 1 FROM {prod_table} p
                WHERE p.transaction_id = s.transaction_id
            )
            {("AND s.id IN (" + id_list + ")") if req.record_ids else ""}
        """),
        {"now": datetime.now().isoformat(), "user": "api"},
    )
    db.commit()

    return PromoteResponse(
        module=req.module,
        requested=requested,
        promoted=promoted.rowcount,
        table_from=staging_table,
        table_to=prod_table,
        confirmation_required=False,
        message=f"{promoted.rowcount} records promoted to {prod_table}.",
    )


# ── Audit Trail ──

@router.get("/audit")
def audit_log(
    limit: int = Query(default=50, le=500),
    module: str = Query(default="", description="Filter by module"),
    db: Session = Depends(get_sync_db),
):
    """View the agent execution audit trail."""
    where = ""
    params: dict = {"limit": limit}
    if module:
        where = "WHERE module = :module"
        params["module"] = module
    rows = db.execute(
        text(f"""
            SELECT id, agent_id, module, source_file, total_rows, passed,
                   warnings, failed, staged, dry_run, summary,
                   started_at, completed_at
            FROM incentivehouse_audit_log
            {where}
            ORDER BY id DESC
            LIMIT :limit
        """),
        params,
    ).fetchall()

    return {
        "audit_records": [
            {
                "id": r.id,
                "agent_id": r.agent_id,
                "module": r.module,
                "source_file": r.source_file,
                "total_rows": r.total_rows,
                "passed": r.passed,
                "warnings": r.warnings,
                "failed": r.failed,
                "staged": r.staged,
                "dry_run": bool(r.dry_run),
                "summary": r.summary,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
            }
            for r in rows
        ]
    }
