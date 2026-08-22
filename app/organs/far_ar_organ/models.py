from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Boolean, Date, Text, Enum, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base
from app.models.base import BaseMixin, BilingualMixin, AuditableMixin


class CustomerStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PARTIALLY_PAID = "partially_paid"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    CREDITED = "credited"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    BANK = "bank"
    CHEQUE = "cheque"
    CARD = "card"
    WIRE = "wire"
    OTHER = "other"


class CreditNoteStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"
    APPLIED = "applied"


class AgingBucket(str, enum.Enum):
    CURRENT = "current"
    DAYS_1_30 = "1_30"
    DAYS_31_60 = "31_60"
    DAYS_61_90 = "61_90"
    OVER_90 = "over_90"


class ARCustomer(Base, BaseMixin, BilingualMixin):
    __tablename__ = "ar_customers"
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    tax_id: Mapped[str] = mapped_column(String(50), nullable=True)
    credit_limit: Mapped[float] = mapped_column(Float, default=0.0)
    credit_used: Mapped[float] = mapped_column(Float, default=0.0)
    risk_rating: Mapped[str] = mapped_column(String(10), default="B")
    payment_terms: Mapped[int] = mapped_column(Integer, default=30)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)
    discount_days: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[CustomerStatus] = mapped_column(Enum(CustomerStatus), default=CustomerStatus.ACTIVE)
    currency_id: Mapped[int] = mapped_column(Integer, ForeignKey("currencies.id"), default=1)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    invoices = relationship("ARInvoice", back_populates="customer")


class ARInvoice(Base, BaseMixin, AuditableMixin):
    __tablename__ = "ar_invoices"
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("ar_customers.id"), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    balance_due: Mapped[float] = mapped_column(Float, default=0.0)
    journal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    currency_id: Mapped[int] = mapped_column(Integer, ForeignKey("currencies.id"), default=1)
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    customer = relationship("ARCustomer", back_populates="invoices")
    lines = relationship("ARInvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("ARPayment", back_populates="invoice")


class ARInvoiceLine(Base, BaseMixin):
    __tablename__ = "ar_invoice_lines"
    invoice_id: Mapped[int] = mapped_column(Integer, ForeignKey("ar_invoices.id"), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)
    tax_rate: Mapped[float] = mapped_column(Float, default=0.0)
    net_amount: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    gl_account_id: Mapped[int] = mapped_column(Integer, nullable=True)
    invoice = relationship("ARInvoice", back_populates="lines")


class ARPayment(Base, BaseMixin, AuditableMixin):
    __tablename__ = "ar_payments"
    payment_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    invoice_id: Mapped[int] = mapped_column(Integer, ForeignKey("ar_invoices.id"), nullable=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("ar_customers.id"), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.BANK)
    reference: Mapped[str] = mapped_column(String(100), nullable=True)
    currency_id: Mapped[int] = mapped_column(Integer, ForeignKey("currencies.id"), default=1)
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)
    journal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    invoice = relationship("ARInvoice", back_populates="payments")
    customer = relationship("ARCustomer")


class ARCreditNote(Base, BaseMixin, AuditableMixin):
    __tablename__ = "ar_credit_notes"
    credit_note_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    invoice_id: Mapped[int] = mapped_column(Integer, ForeignKey("ar_invoices.id"), nullable=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("ar_customers.id"), nullable=False)
    credit_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[CreditNoteStatus] = mapped_column(Enum(CreditNoteStatus), default=CreditNoteStatus.DRAFT)
    journal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    customer = relationship("ARCustomer")


class ARAgingBucket(Base, BaseMixin):
    __tablename__ = "ar_aging_buckets"
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("ar_customers.id"), nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    bucket: Mapped[AgingBucket] = mapped_column(Enum(AgingBucket), nullable=False)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    invoice_count: Mapped[int] = mapped_column(Integer, default=0)
    customer = relationship("ARCustomer")
