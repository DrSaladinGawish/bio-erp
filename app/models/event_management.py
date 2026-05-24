import uuid
from datetime import timezone, date, datetime, timezone
from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Enum as SAEnum,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.base import BaseMixin
import enum


class EventType(str, enum.Enum):
    transaction = "transaction"
    alert = "alert"
    state_change = "state_change"
    audit = "audit"
    sync = "sync"
    branch_access = "branch_access"


class SourceSystem(str, enum.Enum):
    local_bio = "local_bio"
    web_api = "web_api"


class SourceComponent(str, enum.Enum):
    brain = "brain"
    organ = "organ"
    cell = "cell"
    neural_node = "neural_node"
    api = "api"
    sc = "sc"
    ai_bridge = "ai_bridge"
    dashboard = "dashboard"
    branch_filter = "branch_filter"


class Severity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class MigrationStatus(str, enum.Enum):
    pending = "pending"
    synced = "synced"
    failed = "failed"


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    event_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    event_type: Mapped[str] = mapped_column(SAEnum(EventType), nullable=False)
    source_system: Mapped[str] = mapped_column(
        SAEnum(SourceSystem), nullable=False, default=SourceSystem.local_bio
    )
    source_component: Mapped[str] = mapped_column(
        SAEnum(SourceComponent), nullable=False
    )
    source_id: Mapped[str] = mapped_column(String(255), nullable=True)
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    severity: Mapped[str] = mapped_column(
        SAEnum(Severity), nullable=False, default=Severity.info
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    payload: Mapped[dict] = mapped_column(JSON, nullable=True)
    handled: Mapped[bool] = mapped_column(Boolean, default=False)
    handled_by: Mapped[str] = mapped_column(String(255), nullable=True)
    migration_status: Mapped[str] = mapped_column(
        SAEnum(MigrationStatus), default=MigrationStatus.pending
    )


class BranchEventSummary(Base, BaseMixin):
    __tablename__ = "branch_event_summaries"

    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    total_events: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    last_sync_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
