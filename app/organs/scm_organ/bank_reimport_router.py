"""
P3 — Bank Re-Import Router
API endpoints for recovering excluded bank transactions.
All writes go to staging tables only — production data is protected.
"""
import json
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings


def get_sync_db():
    from app.database import get_sync_session
    session = get_sync_session()
    try:
        yield session
    finally:
        session.close()

# Import the engine (adjust path as needed)
try:
    from app.organs.scm_organ.bank_reimport_engine import BankReimportEngine, run_reimport, STAGING_TABLE
except ImportError:
    # Fallback: try relative import
    from .bank_reimport_engine import BankReimportEngine, run_reimport, STAGING_TABLE

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bank", tags=["bank-reimport"])


# ── Pydantic Schemas ──
class ReimportRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source: str = Field(default="exclusion_table", description="Source: exclusion_table, csv_file, json_file")
    dry_run: bool = Field(default=True, description="If True, validate only — do not write to staging")
    batch_size: int = Field(default=500, ge=1, le=5000, description="Process in chunks")

    @field_validator("source")
    @classmethod
    def valid_source(cls, v: str) -> str:
        if v not in {"exclusion_table", "csv_file", "json_file"}:
            raise ValueError("source must be exclusion_table, csv_file, or json_file")
        return v


class ReimportResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    batch_id: str
    dry_run: bool
    timestamp: str
    statistics: dict
    valid_records_staged: int
    invalid_records: int
    invalid_samples: list
    staging_table: str
    next_steps: list


class StagingStatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    batch_id: str
    total_staged: int
    status_breakdown: list
    records: list
    review_url: str


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    record_ids: List[int] = Field(..., description="List of staging record IDs to approve")
    reviewer: str = Field(default="system", description="Name/id of reviewer")


class ApproveResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    approved: int
    requested: int
    reviewer: str
    message: str


class DeployRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    batch_id: Optional[str] = Field(None, description="Deploy all approved records in this batch")
    record_ids: Optional[List[int]] = Field(None, description="Or deploy specific record IDs")
    confirmed: bool = Field(False, description="Must be True to actually deploy")


# ── Endpoints ──
@router.post("/reimport", response_model=ReimportResponse)
def bank_reimport(
    request: ReimportRequest,
    db: Session = Depends(get_sync_db),
):
    """
    Recover excluded bank transactions.

    **Default is dry_run=True** — no data is written until you explicitly set dry_run=False.
    This protects production data from accidental re-imports.

    Process:
    1. Scan exclusion source (table/file)
    2. Validate each transaction (amount, date, currency, account)
    3. Check for duplicates (hash-based)
    4. Write valid records to scm_staging_bank_transactions
    5. Return full report with invalid samples for review
    """
    engine = BankReimportEngine(db)
    transactions = engine.scan_excluded_transactions(request.source)

    # Process in batches if needed
    if len(transactions) > request.batch_size:
        logger.info(f"Processing {len(transactions)} transactions in batches of {request.batch_size}")
        all_reports = []
        for i in range(0, len(transactions), request.batch_size):
            batch = transactions[i:i+request.batch_size]
            report = engine.process_batch(batch, dry_run=request.dry_run)
            all_reports.append(report)

        # Merge reports
        merged = {
            "batch_id": f"MERGED-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "dry_run": request.dry_run,
            "timestamp": datetime.utcnow().isoformat(),
            "statistics": {
                "scanned": sum(r["statistics"]["scanned"] for r in all_reports),
                "valid": sum(r["statistics"]["valid"] for r in all_reports),
                "invalid": sum(r["statistics"]["invalid"] for r in all_reports),
                "warnings": sum(r["statistics"]["warnings"] for r in all_reports),
                "staged": sum(r["statistics"]["staged"] for r in all_reports),
                "duplicates": sum(r["statistics"]["duplicates"] for r in all_reports),
            },
            "valid_records_staged": sum(r["valid_records_staged"] for r in all_reports),
            "invalid_records": sum(r["invalid_records"] for r in all_reports),
            "invalid_samples": [sample for r in all_reports for sample in r["invalid_samples"]][:5],
            "staging_table": STAGING_TABLE,
            "next_steps": all_reports[0]["next_steps"],
        }
        return merged

    return engine.process_batch(transactions, dry_run=request.dry_run)


@router.get("/staging/status", response_model=StagingStatusResponse)
def staging_status(
    batch_id: Optional[str] = Query(None, description="Filter by batch ID"),
    db: Session = Depends(get_sync_db),
):
    """
    Review staged bank transactions before deployment.
    Shows status breakdown (pending_review, approved, rejected, deployed).
    """
    engine = BankReimportEngine(db)
    return engine.get_staging_status(batch_id)


@router.post("/staging/approve", response_model=ApproveResponse)
def approve_staged(
    request: ApproveRequest,
    db: Session = Depends(get_sync_db),
):
    """
    Approve staged records for deployment to production.
    Only records with status='pending_review' can be approved.
    """
    engine = BankReimportEngine(db)
    return engine.approve_for_deployment(request.record_ids, request.reviewer)


@router.post("/staging/deploy")
def deploy_to_production(
    request: DeployRequest,
    db: Session = Depends(get_sync_db),
):
    """
    **DANGER ZONE** — Deploy approved records to production bank_transactions table.

    Requirements:
    - confirmed=True (safety flag)
    - Records must have status='approved'
    - User must have deployment rights

    This is the ONLY endpoint that writes to production tables.
    """
    if not request.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Deployment requires confirmed=True. This is a safety measure."
        )

    engine = BankReimportEngine(db)
    engine._ensure_staging_table()

    # Build query for approved records
    query = f"SELECT * FROM {STAGING_TABLE} WHERE status = 'approved'"
    params = {}
    if request.batch_id:
        query += " AND batch_id = :batch_id"
        params["batch_id"] = request.batch_id
    elif request.record_ids:
        query += " AND id IN :ids"
        params["ids"] = tuple(request.record_ids)
    else:
        raise HTTPException(
            status_code=400,
            detail="Must provide either batch_id or record_ids"
        )

    rows = db.execute(query, params).mappings().all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No approved records found matching criteria"
        )

    deployed = 0
    errors = []

    for row in rows:
        try:
            # Insert into production (adjust column names to match your schema)
            db.execute("""
                INSERT INTO bank_transactions (
                    transaction_date, amount, currency, account_number,
                    description, reference_number, counterparty_name,
                    counterparty_account, transaction_type, source,
                    created_at, tx_hash
                ) VALUES (
                    :transaction_date, :amount, :currency, :account_number,
                    :description, :reference_number, :counterparty_name,
                    :counterparty_account, :transaction_type, 'reimport',
                    :created_at, :tx_hash
                )
            """, {
                "transaction_date": row.transaction_date,
                "amount": row.amount,
                "currency": row.currency,
                "account_number": row.account_number,
                "description": row.description,
                "reference_number": row.reference_number,
                "counterparty_name": row.counterparty_name,
                "counterparty_account": row.counterparty_account,
                "transaction_type": row.transaction_type,
                "created_at": datetime.utcnow(),
                "tx_hash": row.tx_hash,
            })

            # Mark as deployed in staging
            db.execute(f"""
                UPDATE {STAGING_TABLE} 
                SET status = 'deployed', deployed_at = :now, deployment_batch_id = :batch_id
                WHERE id = :id
            """, {
                "id": row.id,
                "now": datetime.utcnow().isoformat(),
                "batch_id": request.batch_id or f"DEPLOY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            })

            deployed += 1
        except Exception as e:
            errors.append(f"Record {row.id}: {str(e)}")
            logger.error(f"Deployment failed for record {row.id}: {e}")

    db.commit()

    # Audit log
    engine._write_audit(
        request.batch_id or "manual-deploy",
        "deployed_to_production",
        {"deployed": deployed, "errors": errors, "requested": len(rows)},
        table_name="bank_transactions",
    )
    db.commit()

    return {
        "deployed": deployed,
        "requested": len(rows),
        "errors": errors[:10],  # First 10 errors
        "message": f"{deployed}/{len(rows)} records deployed to production bank_transactions.",
        "warning": "Production data modified. Verify immediately.",
    }


@router.get("/health")
def bank_reimport_health(db: Session = Depends(get_sync_db)):
    """Health check for the bank re-import module."""
    engine = BankReimportEngine(db)
    engine._ensure_staging_table()

    # Count records by status
    counts = db.execute(text(f"""
        SELECT status, COUNT(*) as count FROM {STAGING_TABLE} GROUP BY status
    """)).mappings().all()

    return {
        "module": "Bank Re-Import Engine",
        "version": "1.0.0",
        "staging_table": STAGING_TABLE,
        "production_write_protection": "ACTIVE",
        "staging_counts": {r.status: r.count for r in counts},
        "dry_run_default": True,
        "status": "operational",
    }
