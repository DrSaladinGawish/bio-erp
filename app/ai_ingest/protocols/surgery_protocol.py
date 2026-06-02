"""
Surgery Protocol (Sergi Protocol) — Incentive House ERP
Atomic DB modifications: snapshot → incision → suture → recovery.
"""
import copy
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_ingest.models import (
    AIDocumentIngestion, AISuggestedTransaction,
    SurgeryAuditLog, SuggestionStatus, SurgeryStatus,
)

logger = logging.getLogger(__name__)


class SurgeryStage(str, Enum):
    PRE_OP = "pre_op"
    INCISION = "incision"
    SUTURE = "suture"
    RECOVERY = "recovery"


@dataclass
class SurgicalSnapshot:
    table_name: str
    row_id: int
    column_data: dict
    captured_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SurgicalLog:
    operation_id: str
    stage: SurgeryStage
    table_name: str
    row_id: int | None
    action: str
    status: str
    detail: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class SurgeryProtocol:

    def __init__(self, db: AsyncSession, performed_by: int = 0):
        self.db = db
        self.operation_id = str(uuid.uuid4())
        self.performed_by = performed_by
        self.snapshots: list[SurgicalSnapshot] = []
        self.log_entries: list[SurgicalLog] = []
        self.rollback_stack: list[Callable] = []

    async def _write_audit(self, stage: SurgeryStage, table: str, row_id: int | None,
                            action: str, status: str, detail: str) -> None:
        entry = SurgicalLog(
            operation_id=self.operation_id, stage=stage,
            table_name=table, row_id=row_id, action=action,
            status=status, detail=detail,
        )
        self.log_entries.append(entry)
        log = SurgeryAuditLog(
            surgery_id=self.operation_id,
            protocol="surgery",
            action=action,
            status=SurgeryStatus.committed if status == "success" else SurgeryStatus.failed,
            table_name=table,
            record_id=row_id,
            error_message=detail if status in ("failed", "rolled_back") else None,
            performed_by=self.performed_by,
        )
        self.db.add(log)
        await self.db.flush()

    async def pre_op_snapshot(self, table_name: str, row_id: int) -> SurgicalSnapshot | None:
        try:
            result = await self.db.execute(
                text(f"SELECT * FROM {table_name} WHERE id = :rid"),
                {"rid": row_id},
            )
            row = result.mappings().first()
            if row:
                data = dict(row)
                snap = SurgicalSnapshot(table_name=table_name, row_id=row_id, column_data=copy.deepcopy(data))
                self.snapshots.append(snap)
                await self._write_audit(SurgeryStage.PRE_OP, table_name, row_id, "snapshot", "success",
                                       f"Captured {len(data)} columns")
                return snap
        except Exception as e:
            await self._write_audit(SurgeryStage.PRE_OP, table_name, row_id, "snapshot", "failed", str(e))
        return None

    async def incision(self, table_name: str, row_id: int | None, action: str,
                       operation: Callable, verify_sql: str | None = None) -> Any:
        try:
            result = operation()
            if hasattr(result, '__await__'):
                result = await result
            await self.db.flush()

            if verify_sql:
                vr = await self.db.execute(text(verify_sql))
                if not vr.scalar():
                    raise RuntimeError(f"Suture check failed: verify_sql returned no result")

            snap = next(
                (s for s in self.snapshots if s.table_name == table_name and s.row_id == row_id),
                None,
            )
            if snap:
                async def rollback_fn(s=snap):
                    restore_sql = text(
                        f"UPDATE {s.table_name} SET {', '.join(f'{k} = :{k}' for k in s.column_data if k != 'id')} WHERE id = :id"
                    )
                    params = {k: v for k, v in s.column_data.items() if k != 'id'}
                    params["id"] = s.row_id
                    await self.db.execute(restore_sql, params)
                    await self.db.flush()
                self.rollback_stack.append(rollback_fn)

            await self._write_audit(SurgeryStage.INCISION, table_name, row_id, action, "success",
                                   "Operation flushed and verified")
            return result
        except Exception as e:
            await self._write_audit(SurgeryStage.INCISION, table_name, row_id, action, "failed", str(e))
            await self.recovery(rollback=True)
            raise

    async def suture(self, table_name: str, row_id: int | None,
                     validation_fn: Callable[[AsyncSession], bool]) -> bool:
        try:
            valid = validation_fn(self.db)
            if hasattr(valid, '__await__'):
                valid = await valid
            if valid:
                await self._write_audit(SurgeryStage.SUTURE, table_name, row_id, "validation", "success",
                                       "Business rule validation passed")
            else:
                await self._write_audit(SurgeryStage.SUTURE, table_name, row_id, "validation", "failed",
                                       "Validation FAILED — rolling back")
                await self.recovery(rollback=True)
                raise RuntimeError(f"Suture validation failed for {table_name}.{row_id}")
            return valid
        except Exception as e:
            await self._write_audit(SurgeryStage.SUTURE, table_name, row_id, "validation", "failed", str(e))
            await self.recovery(rollback=True)
            raise

    async def recovery(self, rollback: bool = False) -> None:
        if rollback:
            for rb in reversed(self.rollback_stack):
                try:
                    await rb()
                except Exception as e:
                    logger.error("Rollback function failed: %s", e)
            await self.db.rollback()
            await self._write_audit(SurgeryStage.RECOVERY, "transaction", None, "rollback", "success",
                                   "All changes rolled back to pre-op state")
        else:
            await self.db.commit()
            await self._write_audit(SurgeryStage.RECOVERY, "transaction", None, "commit", "success",
                                   "All changes committed successfully")

    def get_audit_trail(self) -> list[dict]:
        return [
            {
                "operation_id": e.operation_id,
                "stage": e.stage.value,
                "table": e.table_name,
                "row_id": e.row_id,
                "action": e.action,
                "status": e.status,
                "detail": e.detail,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in self.log_entries
        ]


async def surgical_post_transaction(
    db: AsyncSession, suggestion: AISuggestedTransaction, user_id: int,
    amended: bool = False,
) -> dict:
    sp = SurgeryProtocol(db, performed_by=user_id)
    txn_type = suggestion.transaction_type

    await sp.pre_op_snapshot("ai_suggested_transaction", suggestion.id)

    async def do_insert():
        from datetime import date

        jv_number = f"AI-{'AMEND-' if amended else ''}{suggestion.id}"
        today = date.today()
        description = (suggestion.review_notes or suggestion.description or suggestion.title or "AI-generated JV")[:500]
        total_debit = float(suggestion.total_debit or 0)
        total_credit = float(suggestion.total_credit or 0)
        branch_id = suggestion.branch_id or 1

        result = await db.execute(
            text("""
                INSERT INTO jv_headers (
                    jv_number, jv_date, reference, description,
                    total_debit, total_credit, branch_id,
                    status, gl_posted, created_by, created_at, updated_at,
                    is_active
                ) VALUES (
                    :jv_number, :jv_date, :reference, :description,
                    :total_debit, :total_credit, :branch_id,
                    :status, :gl_posted, :created_by, :created_at, :updated_at,
                    TRUE
                ) RETURNING id
            """),
            {
                "jv_number": jv_number,
                "jv_date": today,
                "reference": f"AI-INGEST-{suggestion.document_id}",
                "description": description,
                "total_debit": total_debit,
                "total_credit": total_credit,
                "branch_id": branch_id,
                "status": "draft",
                "gl_posted": False,
                "created_by": user_id,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        jv_id = result.scalar_one()

        # Resolve line items — multi-key fallback handles upstream key variations
        lines = suggestion.journal_lines or []
        if not lines and suggestion.extracted_entities:
            entities = suggestion.extracted_entities if isinstance(suggestion.extracted_entities, dict) else {}
            lines = entities.get("lines", entities.get("line_items", []))

        if not lines:
            # Balanced single-line fallback from totals
            lines = [{
                "gl_account_id": 0,
                "debit_amount": total_debit,
                "credit_amount": total_credit,
                "description": description,
            }]

        for i, line in enumerate(lines, start=1):
            gl_account_id = int(
                line.get("gl_account_id")
                or line.get("coa_account_id")
                or line.get("account_id")
                or line.get("gl_account")
                or 0
            )
            if gl_account_id > 0:
                chk = await db.execute(text("SELECT id FROM coa_accounts WHERE id = :aid"), {"aid": gl_account_id})
                if not chk.mappings().first():
                    gl_account_id = 0
            if gl_account_id <= 0:
                fallback = await db.execute(text("SELECT id FROM coa_accounts WHERE is_active = TRUE ORDER BY id LIMIT 1"))
                row = fallback.mappings().first()
                gl_account_id = row["id"] if row else 1
            debit_amount = float(
                line.get("debit_amount")
                or line.get("debit")
                or line.get("debit_amt")
                or line.get("dr")
                or 0
            )
            credit_amount = float(
                line.get("credit_amount")
                or line.get("credit")
                or line.get("credit_amt")
                or line.get("cr")
                or 0
            )
            line_desc = (line.get("description") or line.get("desc") or description)[:255]

            await db.execute(
                text("""
                    INSERT INTO jv_lines (
                        jv_id, line_number, gl_account_id,
                        debit_amount, credit_amount, description, created_at, updated_at,
                        is_active
                    ) VALUES (
                        :jv_id, :line_number, :gl_account_id,
                        :debit_amount, :credit_amount, :description, :created_at, :updated_at,
                        TRUE
                    )
                """),
                {
                    "jv_id": jv_id,
                    "line_number": i,
                    "gl_account_id": gl_account_id,
                    "debit_amount": debit_amount,
                    "credit_amount": credit_amount,
                    "description": line_desc,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
            )
        return jv_id

    posted_id = await sp.incision("jv_headers", None, "insert_jv", do_insert,
                                  verify_sql=f"SELECT id FROM jv_headers WHERE id = (SELECT MAX(id) FROM jv_headers)")

    async def validate(s):
        row = await s.execute(text("SELECT id, total_debit FROM jv_headers WHERE id = :id"), {"id": posted_id})
        r = row.mappings().first()
        return r is not None and r["total_debit"] >= 0

    await sp.suture("jv_headers", posted_id, validate)

    async def update_sug():
        suggestion.status = SuggestionStatus.amended if amended else SuggestionStatus.approved
        suggestion.posted_jv_id = posted_id
        suggestion.reviewed_by = user_id
        doc = await db.get(AIDocumentIngestion, suggestion.document_id)
        if doc:
            doc.status = "posted"

    await sp.incision("ai_suggested_transaction", suggestion.id, "update_status", update_sug)
    await sp.recovery(rollback=False)

    return {
        "posted_id": posted_id,
        "table": "jv_headers",
        "operation_id": sp.operation_id,
        "audit_trail": sp.get_audit_trail(),
    }
