"""
P0-A2: Full Audit Trail — Sergey Protocol Implementation
Every CREATE/UPDATE/DELETE logged with before/after state, user, timestamp, IP.
Zero Gap Compliance for audit requirements.
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import Request

from app.organs.incentivehouse_organ.db import get_sync_session_factory
from app.organs.incentivehouse_organ.models_production import AuditLog
from app.organs.incentivehouse_organ.rbac import Permission, require_permission


class AuditAction(str):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    VIEW = "VIEW"


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self._last_hash = self._get_last_hash()

    def _get_last_hash(self) -> Optional[str]:
        last = self.db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        return last.record_hash if last else None

    def _compute_hash(self, data: dict) -> str:
        canonical = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        user_name: str = None,
        user_role: str = None,
        old_values: dict = None,
        new_values: dict = None,
        request: Request = None,
        source_module: str = None,
        source_function: str = None,
        compliance_flag: str = None,
    ) -> AuditLog:
        changed = []
        if old_values and new_values:
            for key in set(old_values.keys()) | set(new_values.keys()):
                if old_values.get(key) != new_values.get(key):
                    changed.append(key)

        record_data = {
            "user_id": user_id,
            "user_name": user_name,
            "user_role": user_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "entity_display": new_values.get("name")
            or new_values.get("event_name")
            or entity_id
            if new_values
            else entity_id,
            "old_values": json.dumps(old_values) if old_values else None,
            "new_values": json.dumps(new_values) if new_values else None,
            "changed_fields": json.dumps(changed) if changed else None,
            "timestamp": datetime.utcnow(),
            "ip_address": request.client.host if request else None,
            "user_agent": request.headers.get("user-agent") if request else None,
            "request_id": request.headers.get("x-request-id") if request else None,
            "source_module": source_module,
            "source_function": source_function,
            "compliance_flag": compliance_flag,
            "previous_hash": self._last_hash,
        }

        record_hash = self._compute_hash(record_data)
        record_data["record_hash"] = record_hash

        log = AuditLog(**record_data)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        self._last_hash = record_hash
        return log

    def log_login(self, user_id: str, success: bool, request: Request = None):
        return self.log(
            action="LOGIN" if success else "LOGIN_FAILED",
            entity_type="auth",
            entity_id=user_id,
            user_id=user_id,
            request=request,
            source_module="auth",
            compliance_flag="SOX",
        )

    def log_export(
        self, user_id: str, entity_type: str, filters: dict, request: Request = None
    ):
        return self.log(
            action="EXPORT",
            entity_type=entity_type,
            entity_id="*",
            user_id=user_id,
            new_values={"filters": filters},
            request=request,
            source_module="export",
            compliance_flag="GDPR",
        )

    def verify_chain(self) -> List[dict]:
        records = self.db.query(AuditLog).order_by(AuditLog.id).all()
        broken = []

        for i, record in enumerate(records):
            data = {
                "user_id": record.user_id,
                "user_name": record.user_name,
                "user_role": record.user_role,
                "action": record.action,
                "entity_type": record.entity_type,
                "entity_id": record.entity_id,
                "entity_display": record.entity_display,
                "old_values": record.old_values,
                "new_values": record.new_values,
                "changed_fields": record.changed_fields,
                "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                "ip_address": record.ip_address,
                "user_agent": record.user_agent,
                "request_id": record.request_id,
                "source_module": record.source_module,
                "source_function": record.source_function,
                "compliance_flag": record.compliance_flag,
                "previous_hash": record.previous_hash,
            }
            computed = self._compute_hash(data)

            if computed != record.record_hash:
                broken.append(
                    {
                        "id": record.id,
                        "expected": computed,
                        "actual": record.record_hash,
                        "severity": "CRITICAL",
                    }
                )

            if i > 0:
                prev = records[i - 1]
                if record.previous_hash != prev.record_hash:
                    broken.append(
                        {
                            "id": record.id,
                            "expected_previous": prev.record_hash,
                            "actual_previous": record.previous_hash,
                            "severity": "HIGH",
                        }
                    )

        return broken


# ── API Router ──

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func


router = APIRouter(prefix="/audit", tags=["Audit"])


def get_db():
    session = get_sync_session_factory()()
    try:
        yield session
    finally:
        session.close()


@router.get("/logs")
def query_audit_logs(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.AUDIT_READ)),
):
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if date_from:
        query = query.filter(AuditLog.timestamp >= date_from)
    if date_to:
        query = query.filter(AuditLog.timestamp <= date_to)

    total = query.count()
    logs = (
        query.order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {"total": total, "page": page, "page_size": page_size, "logs": logs}


@router.get("/verify")
def verify_audit_chain(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.ADMIN)),
):
    audit = AuditService(db)
    broken = audit.verify_chain()
    return {
        "verified": len(broken) == 0,
        "total_records": db.query(AuditLog).count(),
        "broken_links": broken,
        "last_verified": datetime.utcnow().isoformat(),
    }


@router.get("/stats")
def audit_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.AUDIT_READ)),
):
    total = db.query(AuditLog).count()
    today = (
        db.query(AuditLog)
        .filter(func.date(AuditLog.timestamp) == func.current_date())
        .count()
    )
    action_counts = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .group_by(AuditLog.action)
        .all()
    )
    entity_counts = (
        db.query(AuditLog.entity_type, func.count(AuditLog.id))
        .group_by(AuditLog.entity_type)
        .all()
    )
    return {
        "total_records": total,
        "today_count": today,
        "actions": {a: c for a, c in action_counts},
        "entities": {e: c for e, c in entity_counts},
    }
