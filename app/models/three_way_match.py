from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin


class ThreeWayMatch(Base, BaseMixin):
    __tablename__ = "three_way_matches"

    po_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id"), nullable=False
    )
    grn_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grn_headers.id"), nullable=False
    )
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vendor_invoices.id"), nullable=True
    )
    po_qty: Mapped[float] = mapped_column(Float, default=0.0)
    grn_qty: Mapped[float] = mapped_column(Float, default=0.0)
    qty_variance: Mapped[float] = mapped_column(Float, default=0.0)
    qty_tolerance_pct: Mapped[float] = mapped_column(Float, default=5.0)
    qty_match: Mapped[bool] = mapped_column(Boolean, default=False)
    po_price: Mapped[float] = mapped_column(Float, default=0.0)
    invoice_price: Mapped[float] = mapped_column(Float, default=0.0)
    price_variance: Mapped[float] = mapped_column(Float, default=0.0)
    price_tolerance_pct: Mapped[float] = mapped_column(Float, default=2.0)
    price_match: Mapped[bool] = mapped_column(Boolean, default=False)
    overall_status: Mapped[str] = mapped_column(String(20), default="pending")
    match_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    matched_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    remarks: Mapped[str] = mapped_column(Text, nullable=True)

    purchase_order = relationship("PurchaseOrder")
    grn = relationship("GRNHeader")
    invoice = relationship("VendorInvoice")
