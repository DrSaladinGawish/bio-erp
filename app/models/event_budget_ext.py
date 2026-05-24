from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin


class BudgetChange(Base, BaseMixin):
    __tablename__ = "budget_changes"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    change_number: Mapped[str] = mapped_column(String(50), nullable=False)
    change_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="pre_event/post_event"
    )
    original_amount: Mapped[float] = mapped_column(Float, default=0.0)
    revised_amount: Mapped[float] = mapped_column(Float, default=0.0)
    variance: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    approved_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    event = relationship("Event")
    lines = relationship("BudgetChangeLine", back_populates="change")


class BudgetChangeLine(Base, BaseMixin):
    __tablename__ = "budget_change_lines"

    change_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("budget_changes.id"), nullable=False
    )
    budget_version: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_line_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event_budget_lines.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    original_amount: Mapped[float] = mapped_column(Float, default=0.0)
    revised_amount: Mapped[float] = mapped_column(Float, default=0.0)
    variance: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text, nullable=True)

    change = relationship("BudgetChange", back_populates="lines")
    budget_line = relationship("EventBudgetLine")


class BudgetCommitment(Base, BaseMixin):
    __tablename__ = "budget_commitments"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    budget_version: Mapped[int] = mapped_column(Integer, nullable=False)
    budget_line_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event_budget_lines.id"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="PO/JV/Manual"
    )
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_number: Mapped[str] = mapped_column(String(50), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="committed")
    released_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    consumed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    event = relationship("Event")
    budget_line = relationship("EventBudgetLine")
