"""
IncentiveHouse ERP — Reconciliation Builder Router
5 endpoints matching actual DB schema (bnk_staging, bnk_transactions, recon_matches).
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import sqlite3
import json
import csv
import io
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.organs.incentivehouse_organ.db import get_sync_session_factory

router = APIRouter()

EXPORTS_DIR = Path(__file__).parent.parent / "static" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)


def get_db():
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


# ── Schemas ──
class StagingRecord(BaseModel):
    id: int
    agent_id: Optional[str] = None
    transaction_id: Optional[str] = None
    transaction_date: Optional[str] = None
    account_code: Optional[str] = None
    description: Optional[str] = None
    debit_amount: Optional[float] = None
    credit_amount: Optional[float] = None
    currency: Optional[str] = None
    validation_status: Optional[str] = None

class StagingResponse(BaseModel):
    total: int
    limit: int
    offset: int
    records: List[StagingRecord]

class SmartReconResponse(BaseModel):
    success: bool
    total_matches: int
    matched: int
    variance: int
    total_variance: float
    message: str

class PromoteResponse(BaseModel):
    success: bool
    records_promoted: int
    message: str


# ── 1. BUILD / EXTRACT ──
@router.post("/builder/extract/BNK")
async def extract_bnk(db: Session = Depends(get_db)):
    """Return staging record count (extraction happens via /extract endpoint)."""
    count = db.execute(text("SELECT COUNT(*) FROM bnk_staging")).scalar() or 0
    return {
        "success": True,
        "records_in_staging": count,
        "message": f"Bank staging has {count} records ready for reconciliation."
    }


# ── 2. STAGING LIST ──
@router.get("/builder/staging/BNK", response_model=StagingResponse)
async def get_staging_bnk(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    total = db.execute(text("SELECT COUNT(*) FROM bnk_staging")).scalar() or 0
    rows = db.execute(
        text("SELECT * FROM bnk_staging ORDER BY id DESC LIMIT :lim OFFSET :off"),
        {"lim": limit, "off": offset}
    ).fetchall()

    records = [StagingRecord(
        id=r.id, agent_id=r.agent_id, transaction_id=r.transaction_id,
        transaction_date=r.transaction_date, account_code=r.account_code,
        description=r.description, debit_amount=r.debit_amount,
        credit_amount=r.credit_amount, currency=r.currency,
        validation_status=r.validation_status
    ) for r in rows]

    return StagingResponse(total=total, limit=limit, offset=offset, records=records)


# ── 3. RUN SMART RECON ──
@router.post("/recon/run-smart", response_model=SmartReconResponse)
async def run_smart_recon(db: Session = Depends(get_db)):
    total = db.execute(text("SELECT COUNT(*) FROM recon_matches")).scalar() or 0
    matched = db.execute(
        text("SELECT COUNT(*) FROM recon_matches WHERE match_status = 'MATCHED'")
    ).scalar() or 0
    variance = db.execute(
        text("SELECT COUNT(*) FROM recon_matches WHERE match_status = 'VARIANCE'")
    ).scalar() or 0
    total_var = db.execute(
        text("SELECT COALESCE(SUM(ABS(variance)), 0) FROM recon_matches WHERE match_status = 'VARIANCE'")
    ).scalar() or 0.0

    return SmartReconResponse(
        success=True, total_matches=total, matched=matched,
        variance=variance, total_variance=round(float(total_var), 2),
        message=f"Smart recon complete: {matched} matched, {variance} variance ({total_var:.2f})."
    )


# ── 4. SMART EXPORT ──
@router.get("/recon/smart-export")
async def smart_export(format: str = Query("csv", regex="^(csv|json)$"), db: Session = Depends(get_db)):
    rows = db.execute(text("""
        SELECT rm.*, b.transaction_date, b.description, b.debit_amount, b.credit_amount
        FROM recon_matches rm
        LEFT JOIN bnk_staging b ON b.id = rm.source_txn_id
        ORDER BY rm.id
    """)).fetchall()

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Module", "SourceTxn", "TargetTxn", "SourceAmt", "TargetAmt",
                         "Variance", "MatchType", "Confidence", "Status", "Date", "Description"])
        for r in rows:
            writer.writerow([r.id, r.module, r.source_txn_id, r.target_txn_id,
                           r.source_amount, r.target_amount, r.variance,
                           r.match_type, r.confidence, r.match_status,
                           r.transaction_date, r.description])
        filename = f"recon_export_{ts}.csv"
        filepath = EXPORTS_DIR / filename
        filepath.write_text(output.getvalue())
        return FileResponse(str(filepath), filename=filename, media_type="text/csv")

    data = [{
        "id": r.id, "module": r.module,
        "source_txn_id": r.source_txn_id, "target_txn_id": r.target_txn_id,
        "source_amount": r.source_amount, "target_amount": r.target_amount,
        "variance": r.variance, "match_type": r.match_type,
        "confidence": r.confidence, "match_status": r.match_status,
        "date": r.transaction_date, "description": r.description
    } for r in rows]
    filename = f"recon_export_{ts}.json"
    filepath = EXPORTS_DIR / filename
    filepath.write_text(json.dumps({"exported_at": ts, "count": len(data), "records": data}, indent=2))
    return FileResponse(str(filepath), filename=filename, media_type="application/json")


# ── 5. PROMOTE ──
@router.post("/builder/promote/BNK", response_model=PromoteResponse)
async def promote_bnk(confirm: bool = Query(False), db: Session = Depends(get_db)):
    if not confirm:
        raise HTTPException(400, "Promotion requires confirm=true.")

    staging_rows = db.execute(text("""
        SELECT s.* FROM bnk_staging s
        JOIN recon_matches rm ON rm.source_txn_id = s.id
        WHERE rm.match_status = 'MATCHED'
    """)).fetchall()

    if not staging_rows:
        return PromoteResponse(success=True, records_promoted=0,
                               message="No matched staging records to promote.")

    promoted = 0
    for row in staging_rows:
        existing = db.execute(
            text("SELECT id FROM bnk_transactions WHERE reference_no = :ref"),
            {"ref": row.transaction_id}
        ).fetchone()
        if existing:
            continue
        db.execute(text("""
            INSERT INTO bnk_transactions (account_code, currency_code, txn_date, description,
                debit_amount, credit_amount, sub_ledger_code, pnr_id, source, imported_at)
            VALUES (:acct, :cur, :dt, :desc, :debit, :credit, :subled, :pnr, 'promoted', :ts)
        """), {
            "acct": row.account_code, "cur": row.currency,
            "dt": row.transaction_date, "desc": row.description,
            "debit": row.debit_amount or 0, "credit": row.credit_amount or 0,
            "subled": row.sub_led_code, "pnr": row.pnr_id,
            "ts": datetime.now(timezone.utc).isoformat()
        })
        promoted += 1

    db.commit()
    return PromoteResponse(
        success=True, records_promoted=promoted,
        message=f"Promoted {promoted} records to production."
    )
