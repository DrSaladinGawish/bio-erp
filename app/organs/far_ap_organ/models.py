from datetime import datetime, date
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Boolean, Date, Text, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base
from app.models.base import BaseMixin, BilingualMixin, AuditableMixin


class VendorStatus(str, enum.Enum):
    ACTIVE = "active"; INACTIVE = "inactive"; BLOCKED = "blocked"


class BillStatus(str, enum.Enum):
    DRAFT = "draft"; PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"; PARTIALLY_PAID = "partially_paid"
    PAID = "paid"; CANCELLED = "cancelled"; CREDITED = "credited"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"; BANK = "bank"; CHEQUE = "cheque"; CARD = "card"; WIRE = "wire"; OTHER = "other"


class CreditNoteStatus(str, enum.Enum):
    DRAFT = "draft"; POSTED = "posted"; APPLIED = "applied"


class AgingBucket(str, enum.Enum):
    CURRENT = "current"; DAYS_1_30 = "1_30"; DAYS_31_60 = "31_60"
    DAYS_61_90 = "61_90"; OVER_90 = "over_90"


class APVendor(Base, BaseMixin, BilingualMixin):
    __tablename__ = "ap_vendors"
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    tax_id: Mapped[str] = mapped_column(String(50), nullable=True)
    payment_terms: Mapped[int] = mapped_column(Integer, default=30)
    risk_rating: Mapped[str] = mapped_column(String(10), default="B")
    status: Mapped[VendorStatus] = mapped_column(Enum(VendorStatus), default=VendorStatus.ACTIVE)
    currency_id: Mapped[int] = mapped_column(Integer, ForeignKey("currencies.id"), default=1)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    bills = relationship("APBill", back_populates="vendor")


class APBill(Base, BaseMixin, AuditableMixin):
    __tablename__ = "ap_bills"
    bill_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    vendor_id: Mapped[int] = mapped_column(Integer, ForeignKey("ap_vendors.id"), nullable=False)
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[BillStatus] = mapped_column(Enum(BillStatus), default=BillStatus.DRAFT)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    balance_due: Mapped[float] = mapped_column(Float, default=0.0)
    journal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    currency_id: Mapped[int] = mapped_column(Integer, ForeignKey("currencies.id"), default=1)
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)
    approved_by: Mapped[int] = mapped_column(Integer, nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    vendor = relationship("APVendor", back_populates="bills")
    lines = relationship("APBillLine", back_populates="bill", cascade="all, delete-orphan")
    payments = relationship("APPayment", back_populates="bill")


class APBillLine(Base, BaseMixin):
    __tablename__ = "ap_bill_lines"
    bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("ap_bills.id"), nullable=False)
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
    bill = relationship("APBill", back_populates="lines")


class APPayment(Base, BaseMixin, AuditableMixin):
    __tablename__ = "ap_payments"
    payment_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("ap_bills.id"), nullable=True)
    vendor_id: Mapped[int] = mapped_column(Integer, ForeignKey("ap_vendors.id"), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.BANK)
    reference: Mapped[str] = mapped_column(String(100), nullable=True)
    currency_id: Mapped[int] = mapped_column(Integer, ForeignKey("currencies.id"), default=1)
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)
    journal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    bill = relationship("APBill", back_populates="payments")
    vendor = relationship("APVendor")


class APCreditNote(Base, BaseMixin, AuditableMixin):
    __tablename__ = "ap_credit_notes"
    credit_note_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("ap_bills.id"), nullable=True)
    vendor_id: Mapped[int] = mapped_column(Integer, ForeignKey("ap_vendors.id"), nullable=False)
    credit_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[CreditNoteStatus] = mapped_column(Enum(CreditNoteStatus), default=CreditNoteStatus.DRAFT)
    journal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    vendor = relationship("APVendor")


class APApprovalQueue(Base, BaseMixin):
    __tablename__ = "ap_approval_queue"
    bill_id: Mapped[int] = mapped_column(Integer, ForeignKey("ap_bills.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    assigned_to: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    bill = relationship("APBill")
