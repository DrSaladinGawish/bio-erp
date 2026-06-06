"""
intelligence/health.py
System health checks for the IHE-ERP intelligence layer.

Adapted from Bio-ERP: checks IHE_ERP DB connection, counts tables, counts records
per table, computes a data quality score, reports last backup time.

Endpoint: GET /api/v1/intelligence/health returns
  {db_status, table_counts, total_records, data_quality_score, last_backup}
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.organs.incentivehouse_organ.models import (
    PRODUCTION_TABLE_NAMES, STAGING_TABLE_NAMES,
)

logger = logging.getLogger("incentivehouse_organ.intelligence.health")


# Tables we consider "core" for the IHE-ERP business domain
CORE_TABLES = [
    "pnr_master", "events", "sales_invoice", "sales_invoice_line",
    "purchase_voucher", "purchase_voucher_line", "bank_transaction",
    "journal_voucher", "journal_voucher_line", "clients", "vendors",
    "chart_of_accounts",
]


def _safe_count(db: Session, table: str) -> Optional[int]:
    """Count rows in a table; return None if the table does not exist."""
    try:
        return db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
    except Exception as exc:
        logger.debug("count(%s) failed: %s", table, exc)
        return None


def get_health_report(db: Session) -> dict:
    """
    Build a comprehensive health report for the IHE-ERP system.

    Returns a dict with: db_status, table_counts, total_records,
    data_quality_score, last_backup, generated_at, version.
    """
    report: dict[str, Any] = {
        "version": "2.3.0",
        "generated_at": datetime.now().isoformat(),
        "db_status": "unknown",
        "table_counts": {},
        "total_records": 0,
        "core_table_status": {},
        "data_quality_score": 0.0,
        "last_backup": None,
        "warnings": [],
    }

    # 1. DB connectivity
    try:
        db.execute(text("SELECT 1"))
        report["db_status"] = "ok"
    except Exception as exc:
        report["db_status"] = "error"
        report["warnings"].append(f"DB connectivity failed: {exc}")
        return report

    # 2. Per-table counts
    total = 0
    seen = 0
    for table in CORE_TABLES:
        n = _safe_count(db, table)
        report["table_counts"][table] = n
        if n is not None:
            total += n
            seen += 1
        else:
            report["warnings"].append(f"Core table missing or unreadable: {table}")
    report["total_records"] = total

    # 3. Staging + production table presence
    for mod, table in STAGING_TABLE_NAMES.items():
        report["table_counts"][f"stg_{mod}"] = _safe_count(db, table)
    for mod, table in PRODUCTION_TABLE_NAMES.items():
        report["table_counts"][f"prod_{mod}"] = _safe_count(db, table)

    # 4. Core coverage (% of core tables present)
    coverage = (seen / len(CORE_TABLES)) if CORE_TABLES else 0.0

    # 5. Data quality score (0..100)
    #    50% weight on coverage, 50% on having data in core tables
    nonempty = sum(1 for t in CORE_TABLES if (report["table_counts"].get(t) or 0) > 0)
    nonempty_ratio = (nonempty / len(CORE_TABLES)) if CORE_TABLES else 0.0
    report["data_quality_score"] = round(100.0 * (0.5 * coverage + 0.5 * nonempty_ratio), 1)
    report["core_table_status"] = {
        "present": seen,
        "missing": len(CORE_TABLES) - seen,
        "total_core": len(CORE_TABLES),
        "nonempty": nonempty,
    }

    # 6. Last backup (read from backup_log if present)
    try:
        row = db.execute(text("""
            SELECT MAX(timestamp) FROM audit_trail WHERE action = 'BACKUP'
        """)).scalar()
        report["last_backup"] = row
    except Exception:
        report["last_backup"] = None

    return report


def get_data_quality_score(db: Session) -> float:
    """Return just the data quality score (0..100)."""
    return get_health_report(db).get("data_quality_score", 0.0)
