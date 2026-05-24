from datetime import timezone, datetime, timezone
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin


BUDGET_VERSIONS = {1: "Conceptual", 2: "Executable", 3: "Final"}
BUDGET_LIFECYCLE_STATUSES = ["Draft", "Submitted", "Approved", "Locked", "Rejected"]


class BudgetLifecycle(Base, BaseMixin):
    __tablename__ = "budget_lifecycles"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False, unique=True
    )
    v1_status: Mapped[str] = mapped_column(String(20), default="Draft")
    v1_submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    v1_approved_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    v1_approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    v1_locked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    v1_locked_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    v2_status: Mapped[str] = mapped_column(String(20), default="Draft")
    v2_submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    v2_approved_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    v2_approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    v2_locked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    v2_locked_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    v3_status: Mapped[str] = mapped_column(String(20), default="Draft")
    v3_submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    v3_approved_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    v3_approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    v3_locked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    v3_locked_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    current_active_version: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    event = relationship("Event")


class BudgetSnapshot(Base, BaseMixin):
    __tablename__ = "budget_snapshots"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    budget_version: Mapped[int] = mapped_column(Integer, nullable=False)
    line_data: Mapped[str] = mapped_column(
        Text, nullable=False, comment="JSON snapshot of budget lines"
    )
    total_budget: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    gross_profit: Mapped[float] = mapped_column(Float, default=0.0)
    snapshot_taken_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    taken_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    notes: Mapped[str] = mapped_column(String(500), nullable=True)
