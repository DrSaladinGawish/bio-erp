from sqlalchemy import Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BranchAwareMixin


class Staff(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "staff"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(100), nullable=True)
    department: Mapped[str] = mapped_column(String(100), nullable=True)
    cost_center: Mapped[str] = mapped_column(String(50), nullable=True)
    ap_account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("coa_accounts.id"),
        nullable=True,
        comment="Accounts Payable",
    )
    exp_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True, comment="Expense Account"
    )
    salary: Mapped[float] = mapped_column(Float, default=0.0)
    hire_date: Mapped[str] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    ap_account = relationship("COAAccount", foreign_keys=[ap_account_id])
    exp_account = relationship("COAAccount", foreign_keys=[exp_account_id])


class FieldTask(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "field_tasks"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    staff_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("staff.id"), nullable=False
    )
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="PENDING", comment="PENDING/IN_PROGRESS/COMPLETED"
    )
    scheduled_date: Mapped[str] = mapped_column(String(10), nullable=True)
    completed_date: Mapped[str] = mapped_column(String(10), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
