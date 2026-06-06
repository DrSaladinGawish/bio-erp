"""
intelligence/audit.py
AuditTrail model + audit_event() function for the IHE-ERP intelligence layer.

Adapted from Bio-ERP: writes to the IHE_ERP SQL Server (not PostgreSQL).
All audit records are written to the audit_trail table.

Usage:
    from app.organs.incentivehouse_organ.intelligence.audit import audit_event, AuditTrail

    audit_event(db, "sales_invoice", "123", "CREATE", None, payload, user="admin")
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, text
from sqlalchemy.orm import Session

logger = logging.getLogger("incentivehouse_organ.intelligence.audit")


# ============================================================================
# Schema (auto-created on first boot via main._ensure_tables_sync)
# ============================================================================

AUDIT_TRAIL_DDL = """
CREATE TABLE IF NOT EXISTS audit_trail (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id TEXT,
    action TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    user_id TEXT,
    ip_address TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    extra TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_table_name ON audit_trail(table_name);
CREATE INDEX IF NOT EXISTS ix_audit_record_id ON audit_trail(record_id);
CREATE INDEX IF NOT EXISTS ix_audit_timestamp ON audit_trail(timestamp);
"""


# ============================================================================
# ORM-style wrapper (lightweight - we use raw SQL for cross-DB compatibility)
# ============================================================================

class AuditTrail:
    """Lightweight DTO for an audit record."""

    __slots__ = (
        "id", "table_name", "record_id", "action",
        "old_value", "new_value", "user_id", "ip_address",
        "timestamp", "extra",
    )

    def __init__(self, **kwargs):
        for k in self.__slots__:
            setattr(self, k, kwargs.get(k))
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__slots__}


# ============================================================================
# Public API
# ============================================================================

def audit_event(
    db: Session,
    table_name: str,
    record_id: Optional[str],
    action: str,
    old_value: Any = None,
    new_value: Any = None,
    user_id: str = "system",
    ip_address: Optional[str] = None,
    extra: Optional[dict] = None,
) -> int:
    """
    Record an audit event.

    Args:
        db:          SQLAlchemy session
        table_name:  Business table being audited (e.g. "sales_invoice")
        record_id:   Primary key of the affected row
        action:      One of CREATE / UPDATE / DELETE / LOGIN / EXPORT
        old_value:   Previous value (will be JSON-encoded)
        new_value:   New value (will be JSON-encoded)
        user_id:     Username or "system"
        ip_address:  Client IP if available
        extra:       Arbitrary dict (will be JSON-encoded)

    Returns:
        The new audit_trail.id, or -1 on failure (failures are logged, never raised)
    """
    try:
        old_json = json.dumps(old_value, default=str) if old_value is not None else None
        new_json = json.dumps(new_value, default=str) if new_value is not None else None
        extra_json = json.dumps(extra, default=str) if extra else None
        result = db.execute(
            text("""
                INSERT INTO audit_trail
                    (table_name, record_id, action, old_value, new_value,
                     user_id, ip_address, timestamp, extra)
                VALUES
                    (:table_name, :record_id, :action, :old_value, :new_value,
                     :user_id, :ip_address, :timestamp, :extra)
            """),
            {
                "table_name": table_name,
                "record_id": str(record_id) if record_id is not None else None,
                "action": action,
                "old_value": old_json,
                "new_value": new_json,
                "user_id": user_id,
                "ip_address": ip_address,
                "timestamp": datetime.now().isoformat(),
                "extra": extra_json,
            },
        )
        db.commit()
        return result.lastrowid or -1
    except Exception as exc:
        logger.warning("audit_event failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
        return -1


def query_audit(
    db: Session,
    table_name: Optional[str] = None,
    record_id: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    since: Optional[str] = None,
) -> list:
    """Query audit records with optional filters."""
    where = []
    params: dict = {"limit": limit}
    if table_name:
        where.append("table_name = :table_name")
        params["table_name"] = table_name
    if record_id:
        where.append("record_id = :record_id")
        params["record_id"] = record_id
    if action:
        where.append("action = :action")
        params["action"] = action
    if user_id:
        where.append("user_id = :user_id")
        params["user_id"] = user_id
    if since:
        where.append("timestamp >= :since")
        params["since"] = since
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT id, table_name, record_id, action, user_id, ip_address, timestamp
        FROM audit_trail
        {where_sql}
        ORDER BY id DESC
        LIMIT :limit
    """
    rows = db.execute(text(sql), params).fetchall()
    return [dict(r._mapping) for r in rows]


def count_audit(db: Session) -> int:
    """Total audit records."""
    try:
        return db.execute(text("SELECT COUNT(*) FROM audit_trail")).scalar() or 0
    except Exception:
        return 0
