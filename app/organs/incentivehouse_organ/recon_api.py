import sqlite3
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/recon", tags=["Reconciliation"])

STAGING_DB = Path("D:/ERP_Ecosystem/46_Protocell_Migration/protocell_staging.db")

def get_staging_conn():
    return sqlite3.connect(str(STAGING_DB))

class ReconStatus(BaseModel):
    recon_status: str
    count: int
    total_variance: float

class VarianceItem(BaseModel):
    check_book_id: int
    check_book_name: str
    transaction_id: str
    variance: float
    recon_status: str

@router.get("/status", response_model=List[ReconStatus])
def recon_status():
    conn = get_staging_conn()
    c = conn.cursor()
    c.execute("""
        SELECT recon_status, COUNT(*), SUM(ABS(variance))
        FROM bnk_reconciliation
        GROUP BY recon_status
    """)
    rows = c.fetchall()
    conn.close()
    return [{"recon_status": r[0], "count": r[1], "total_variance": r[2] or 0} for r in rows]

@router.get("/variances", response_model=List[VarianceItem])
def recon_variances(limit: int = 20):
    conn = get_staging_conn()
    c = conn.cursor()
    c.execute("""
        SELECT check_book_id, check_book_name, transaction_id, variance, recon_status
        FROM bnk_reconciliation
        WHERE recon_status != 'RECONCILED'
        ORDER BY ABS(variance) DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [{
        "check_book_id": r[0], "check_book_name": r[1],
        "transaction_id": r[2], "variance": r[3], "recon_status": r[4]
    } for r in rows]

@router.get("/check-books")
def check_books():
    conn = get_staging_conn()
    c = conn.cursor()
    c.execute("""
        SELECT check_book_id, check_book_name, COUNT(*) as total,
               SUM(CASE WHEN recon_status='RECONCILED' THEN 1 ELSE 0 END) as ok,
               SUM(CASE WHEN recon_status!='RECONCILED' THEN 1 ELSE 0 END) as bad
        FROM bnk_reconciliation
        GROUP BY check_book_id, check_book_name
        ORDER BY check_book_id
    """)
    rows = c.fetchall()
    conn.close()
    return [{"cb_id": r[0], "name": r[1], "total": r[2], "ok": r[3], "bad": r[4]} for r in rows]
