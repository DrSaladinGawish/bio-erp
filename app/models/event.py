from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BranchAwareMixin, CurrencyAwareMixin


class PNR(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "pnrs"

    pnr_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="PNR-XXXXXXXX"
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    balance: Mapped[float] = mapped_column(Float, default=0.0)

    event = relationship("Event", back_populates="pnrs")
    client = relationship("Client")


class Event(Base, BaseMixin, BranchAwareMixin, CurrencyAwareMixin):
    __tablename__ = "events"

    event_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="EVT-YYYY-NNN"
    )
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=False
    )
    project_manager_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("staff.id"), nullable=True
    )
    name_en: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="CONCEPT",
        comment="CONCEPT/BUDGETED/APPROVED/IN_PROGRESS/COMPLETED/CLOSED/CANCELLED",
    )
    budget_version: Mapped[int] = mapped_column(Integer, default=1)
    event_type: Mapped[str] = mapped_column(String(100), nullable=True)
    start_date: Mapped[str] = mapped_column(String(10), nullable=True)
    end_date: Mapped[str] = mapped_column(String(10), nullable=True)
    venue: Mapped[str] = mapped_column(String(255), nullable=True)
    venue_ar: Mapped[str] = mapped_column(String(255), nullable=True)
    booth_size: Mapped[str] = mapped_column(String(50), nullable=True)
    booth_option: Mapped[str] = mapped_column(
        String(20), nullable=True, comment="BASIC/PREMIUM/VIP"
    )
    duration_days: Mapped[int] = mapped_column(Integer, default=1)
    total_budget: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    gross_profit: Mapped[float] = mapped_column(Float, default=0.0)
    approved_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    design_attachment: Mapped[str] = mapped_column(String(500), nullable=True)

    client = relationship("Client")
    project_manager = relationship("Staff")
    pnrs = relationship("PNR", back_populates="event")
    budget_lines = relationship("EventBudgetLine", back_populates="event")
    line_items = relationship("EventLineItem", back_populates="event")


class EventBudgetLine(Base, BaseMixin, CurrencyAwareMixin):
    __tablename__ = "event_budget_lines"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    master_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event_master_nodes.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    markup_percent: Mapped[float] = mapped_column(Float, default=0.12)
    selling_price: Mapped[float] = mapped_column(Float, default=0.0)
    budget_version: Mapped[int] = mapped_column(Integer, default=1)
    revision_reason: Mapped[str] = mapped_column(String(500), nullable=True)
    section: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        comment="BOOTH/EQUIPMENT/FURNITURE/STAFFING/GIVEAWAYS",
    )
    archived_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    event = relationship("Event", back_populates="budget_lines")
    currency = relationship("Currency")


class EventLineItem(Base, BaseMixin):
    __tablename__ = "event_line_items"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    master_node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event_master_nodes.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    description_ar: Mapped[str] = mapped_column(String(500), nullable=True)
    section: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="BOOTH/EQUIPMENT/FURNITURE/STAFFING/GIVEAWAYS",
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    uom: Mapped[str] = mapped_column(String(20), nullable=True)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    selling_price: Mapped[float] = mapped_column(Float, default=0.0)
    markup_percent: Mapped[float] = mapped_column(Float, default=0.12)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=True
    )
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    event = relationship("Event", back_populates="line_items")
    item = relationship("EventMasterNode", foreign_keys=[master_node_id])


class EventDoc(Base, BaseMixin):
    __tablename__ = "event_docs"

    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
