from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin


class ApprovalRule(Base, BaseMixin):
    __tablename__ = "approval_rules"

    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="PO/PMT/RCT/JV/BudgetChange"
    )
    min_amount: Mapped[float] = mapped_column(Float, default=0.0)
    max_amount: Mapped[float] = mapped_column(Float, nullable=True)
    role_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    can_delegate: Mapped[bool] = mapped_column(Boolean, default=True)
    escalation_hours: Mapped[int] = mapped_column(Integer, default=24)
    escalation_role_id: Mapped[int] = mapped_column(Integer, nullable=True)

    user = relationship("User", foreign_keys=[user_id])


class ApprovalInstance(Base, BaseMixin):
    __tablename__ = "approval_instances"

    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    document_number: Mapped[str] = mapped_column(String(50), nullable=True)
    requester_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    total_steps: Mapped[int] = mapped_column(Integer, default=1)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    requester = relationship("User", foreign_keys=[requester_id])
    steps = relationship("ApprovalStep", back_populates="instance")


class ApprovalStep(Base, BaseMixin):
    __tablename__ = "approval_steps"

    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_instances.id"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    rule_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_rules.id"), nullable=True
    )
    approver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    role_id: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    decision: Mapped[str] = mapped_column(String(20), nullable=True)
    comments: Mapped[str] = mapped_column(Text, nullable=True)
    acted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    instance = relationship("ApprovalInstance", back_populates="steps")
    approver = relationship("User", foreign_keys=[approver_id])


class DocumentSequence(Base, BaseMixin):
    __tablename__ = "document_sequences"

    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    prefix: Mapped[str] = mapped_column(String(20), nullable=True)
    current_number: Mapped[int] = mapped_column(Integer, default=0)
    suffix: Mapped[str] = mapped_column(String(20), nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    month: Mapped[int] = mapped_column(Integer, nullable=True)
    padding: Mapped[int] = mapped_column(Integer, default=5)
