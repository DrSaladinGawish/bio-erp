from datetime import timezone, datetime, timezone
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BranchAwareMixin


class EInvoiceRegister(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "e_invoice_register"

    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    uuid: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=True, comment="ETA assigned UUID"
    )
    pnr_id: Mapped[int] = mapped_column(Integer, ForeignKey("pnrs.id"), nullable=True)
    sales_invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("net_sales.id"), nullable=True
    )
    invoice_type: Mapped[str] = mapped_column(
        String(20), default="SALES", comment="SALES/PURCHASE/DEBIT_NOTE/CREDIT_NOTE"
    )
    issue_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    origin_currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False
    )
    origin_amount: Mapped[float] = mapped_column(Float, default=0.0)
    conversion_rate: Mapped[float] = mapped_column(Float, default=1.0)
    total_amount_egp: Mapped[float] = mapped_column(Float, default=0.0)
    vat_amount: Mapped[float] = mapped_column(Float, default=0.0)
    net_amount: Mapped[float] = mapped_column(Float, default=0.0)
    eta_status: Mapped[str] = mapped_column(
        String(20), default="PENDING", comment="PENDING/SUBMITTED/VALID/REJECTED"
    )
    eta_submission_id: Mapped[str] = mapped_column(String(100), nullable=True)
    eta_response: Mapped[str] = mapped_column(Text, nullable=True)
    eta_submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    qr_code: Mapped[str] = mapped_column(Text, nullable=True)
    signed_xml: Mapped[str] = mapped_column(Text, nullable=True)
    is_synced: Mapped[bool] = mapped_column(Boolean, default=False)


class EInvoiceGLEntry(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "e_invoice_gl_entries"

    einvoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("e_invoice_register.id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    debit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    credit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    einvoice = relationship("EInvoiceRegister")
    account = relationship("COAAccount")
