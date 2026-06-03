"""
Bank Reconciliation API — FastAPI router using proper dependency injection.

Reads reconciliation data from the project-managed SQLite DB (same engine
as the rest of the IncentiveHouse organ), so paths and connection pooling
stay consistent.

Endpoints (under /recon):
  GET /recon/status          - per-status counts + variance totals
  GET /recon/variances       - largest unreconciled variances
  GET /recon/check-books     - per-check-book rollup
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.organs.incentivehouse_organ.db import get_sync_session_factory

router = APIRouter(prefix="/recon", tags=["reconciliation"])


def get_recon_db() -> Session:
    """Yield a sync SQLAlchemy session pointed at the IncentiveHouse DB."""
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def _table_exists(db: Session, name: str) -> bool:
    try:
        row = db.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:n"),
            {"n": name},
        ).fetchone()
        return row is not None
    except Exception:
        return False


@router.get("/status")
def recon_status(db: Session = Depends(get_recon_db)):
    """Per-status counts and total variance."""
    if not _table_exists(db, "bnk_reconciliation"):
        return {"rows": [], "note": "bnk_reconciliation table not yet created"}
    rows = db.execute(text("""
        SELECT recon_status, COUNT(*) AS cnt, COALESCE(SUM(ABS(variance)), 0) AS total_variance
        FROM bnk_reconciliation
        GROUP BY recon_status
        ORDER BY cnt DESC
    """)).fetchall()
    return {
        "rows": [
            {
                "recon_status": r.recon_status or "UNKNOWN",
                "count": int(r.cnt or 0),
                "total_variance": float(r.total_variance or 0),
            }
            for r in rows
        ]
    }


@router.get("/variances")
def recon_variances(
    limit: int = Query(default=20, ge=1, le=500),
    db: Session = Depends(get_recon_db),
):
    """Top unreconciled variances by absolute size."""
    if not _table_exists(db, "bnk_reconciliation"):
        return {"rows": [], "note": "bnk_reconciliation table not yet created"}
    rows = db.execute(text("""
        SELECT id, check_book_id, check_book_name, transaction_id,
               variance, bank_amount, gl_amount, recon_status
        FROM bnk_reconciliation
        WHERE COALESCE(recon_status, '') != 'RECONCILED'
        ORDER BY ABS(COALESCE(variance, 0)) DESC
        LIMIT :limit
    """), {"limit": limit}).fetchall()
    return {
        "rows": [
            {
                "id": int(r.id),
                "check_book_id": r.check_book_id,
                "check_book_name": r.check_book_name,
                "transaction_id": r.transaction_id,
                "variance": float(r.variance or 0),
                "bank_amount": float(r.bank_amount or 0),
                "gl_amount": float(r.gl_amount or 0),
                "recon_status": r.recon_status,
            }
            for r in rows
        ]
    }


@router.get("/check-books")
def check_books(db: Session = Depends(get_recon_db)):
    """Per-check-book rollup."""
    if not _table_exists(db, "bnk_reconciliation"):
        return {"rows": [], "note": "bnk_reconciliation table not yet created"}
    rows = db.execute(text("""
        SELECT check_book_id, check_book_name, COUNT(*) AS total,
               SUM(CASE WHEN COALESCE(recon_status,'') = 'RECONCILED' THEN 1 ELSE 0 END) AS ok,
               SUM(CASE WHEN COALESCE(recon_status,'') != 'RECONCILED' THEN 1 ELSE 0 END) AS bad,
               COALESCE(SUM(ABS(variance)), 0) AS total_variance
        FROM bnk_reconciliation
        GROUP BY check_book_id, check_book_name
        ORDER BY check_book_id
    """)).fetchall()
    return {
        "rows": [
            {
                "cb_id": r.check_book_id,
                "name": r.check_book_name,
                "total": int(r.total or 0),
                "ok": int(r.ok or 0),
                "bad": int(r.bad or 0),
                "total_variance": float(r.total_variance or 0),
            }
            for r in rows
        ]
    }
