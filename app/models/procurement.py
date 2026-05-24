from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BranchAwareMixin


class GRNHeader(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "grn_headers"

    grn_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="GRN-YYYY-NNNN"
    )
    po_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    grn_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    received_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    delivery_note_no: Mapped[str] = mapped_column(String(100), nullable=True)
    warehouse_location: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    po = relationship("PurchaseOrder")
    supplier = relationship("Supplier")
    lines = relationship("GRNDetail", back_populates="grn")


class GRNDetail(Base, BaseMixin):
    __tablename__ = "grn_details"

    grn_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grn_headers.id"), nullable=False
    )
    po_line_id: Mapped[int] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(200), nullable=True)
    ordered_qty: Mapped[float] = mapped_column(Float, default=0.0)
    received_qty: Mapped[float] = mapped_column(Float, default=0.0)
    accepted_qty: Mapped[float] = mapped_column(Float, default=0.0)
    rejected_qty: Mapped[float] = mapped_column(Float, default=0.0)
    rejection_reason: Mapped[str] = mapped_column(String(200), nullable=True)
    condition: Mapped[str] = mapped_column(String(20), default="Good")
    inspection_notes: Mapped[str] = mapped_column(Text, nullable=True)

    grn = relationship("GRNHeader", back_populates="lines")


class ServiceConfirmation(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "service_confirmations"

    po_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id"), nullable=False
    )
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    service_description: Mapped[str] = mapped_column(String(500), nullable=False)
    completion_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    quality_rating: Mapped[int] = mapped_column(Integer, default=3)
    performance_notes: Mapped[str] = mapped_column(Text, nullable=True)
    confirmed_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="Confirmed")

    po = relationship("PurchaseOrder")
    supplier = relationship("Supplier")
