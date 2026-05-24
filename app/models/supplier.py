from datetime import timezone, datetime, timezone
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import (
    BaseMixin,
    BilingualMixin,
    BranchAwareMixin,
    CurrencyAwareMixin,
)


class Supplier(Base, BaseMixin, BilingualMixin, BranchAwareMixin):
    __tablename__ = "suppliers"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)
    tax_id: Mapped[str] = mapped_column(String(50), nullable=True)
    commercial_registration: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone1: Mapped[str] = mapped_column(String(50), nullable=True)
    phone2: Mapped[str] = mapped_column(String(50), nullable=True)
    address_en: Mapped[str] = mapped_column(String(500), nullable=True)
    address_ar: Mapped[str] = mapped_column(String(500), nullable=True)
    service_category: Mapped[str] = mapped_column(String(100), nullable=True)
    rating: Mapped[float] = mapped_column(
        Float, default=0.0, comment="0-5 performance score"
    )
    acc_key: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True
    )
    notes: Mapped[str] = mapped_column(String(1000), nullable=True)

    account = relationship("COAAccount", foreign_keys=[acc_key])


class RFQ(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "rfqs"

    rfq_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="RFQ-YYYY-NNNN"
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="DRAFT", comment="DRAFT/SENT/AWARDED/CLOSED"
    )
    issue_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    closing_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), default=1
    )
    total_amount_egp: Mapped[float] = mapped_column(Float, default=0.0)

    quotes = relationship("SupplierQuote", back_populates="rfq")
    purchase_orders = relationship("PurchaseOrder", back_populates="rfq")


class SupplierQuote(Base, BaseMixin):
    __tablename__ = "supplier_quotes"

    rfq_id: Mapped[int] = mapped_column(Integer, ForeignKey("rfqs.id"), nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False
    )
    quote_number: Mapped[str] = mapped_column(String(50), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    amount_egp: Mapped[float] = mapped_column(Float, default=0.0)
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), default=1
    )
    conversion_rate: Mapped[float] = mapped_column(Float, default=1.0)
    delivery_days: Mapped[int] = mapped_column(Integer, nullable=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_awarded: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    rfq = relationship("RFQ", back_populates="quotes")
    supplier = relationship("Supplier")


class PurchaseOrder(Base, BaseMixin, CurrencyAwareMixin):
    __tablename__ = "purchase_orders"

    po_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="PO-YYYY-NNNN"
    )
    rfq_id: Mapped[int] = mapped_column(Integer, ForeignKey("rfqs.id"), nullable=True)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    vat_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    issue_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    delivery_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    rfq = relationship("RFQ", back_populates="purchase_orders")
    supplier = relationship("Supplier")
