from datetime import timezone, datetime
from sqlalchemy import Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), index=True
    )
    actor_id: Mapped[int] = mapped_column(
        Integer, nullable=True, comment="User ID who performed action"
    )
    actor_name: Mapped[str] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="CREATE/UPDATE/DELETE/LOGIN/APPROVE/REJECT"
    )
    target_type: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Table/entity name"
    )
    target_id: Mapped[int] = mapped_column(Integer, nullable=True)
    old_value: Mapped[str] = mapped_column(
        Text, nullable=True, comment="JSON of previous values"
    )
    new_value: Mapped[str] = mapped_column(
        Text, nullable=True, comment="JSON of new values"
    )
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(500), nullable=True)
    branch_id: Mapped[int] = mapped_column(Integer, default=1)
    row_hash: Mapped[str] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hex of this row"
    )
    previous_hash: Mapped[str] = mapped_column(
        String(64), nullable=True, comment="SHA-256 hex of previous row (NULL for genesis)"
    )
    chain_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Whether chain integrity has been verified"
    )
