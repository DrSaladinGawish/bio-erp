import hashlib
import json
from datetime import datetime
from datetime import timezone, date
from decimal import Decimal
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog
from app.models.auth import User


class AuditJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (datetime, date)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


def compute_row_hash(
    timestamp: datetime,
    action: str,
    target_type: str,
    target_id: int | None,
    old_value: str | None,
    new_value: str | None,
    previous_hash: str | None,
) -> str:
    raw = (
        f"{timestamp.isoformat()}:{action}:{target_type}:{target_id}:"
        f"{old_value}:{new_value}:{previous_hash or ''}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()


class AuditLogger:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        action: str,
        target_type: str,
        target_id: int | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        description: str | None = None,
        actor_id: int | None = None,
        actor_name: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        branch_id: int = 1,
    ):
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        old_json = json.dumps(old_value, cls=AuditJSONEncoder) if old_value else None
        new_json = json.dumps(new_value, cls=AuditJSONEncoder) if new_value else None

        # Get last entry's hash for chain
        prev_result = await self.session.execute(
            select(AuditLog.row_hash)
            .order_by(desc(AuditLog.id))
            .limit(1)
        )
        previous_hash = prev_result.scalar_one_or_none()

        row_hash = compute_row_hash(
            timestamp, action, target_type, target_id,
            old_json, new_json, previous_hash,
        )

        entry = AuditLog(
            timestamp=timestamp,
            actor_id=actor_id,
            actor_name=actor_name,
            action=action,
            target_type=target_type,
            target_id=target_id,
            old_value=old_json,
            new_value=new_json,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            branch_id=branch_id,
            row_hash=row_hash,
            previous_hash=previous_hash,
        )
        self.session.add(entry)
        return entry


async def log_action(
    db: AsyncSession,
    user: User,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    description: str | None = None,
):
    logger = AuditLogger(db)
    await logger.log(
        action=action,
        target_type=entity_type,
        target_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        description=description,
        actor_id=user.id,
        actor_name=user.username,
    )
