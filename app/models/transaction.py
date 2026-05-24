from datetime import timezone, datetime, timezone
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BranchAwareMixin, CurrencyAwareMixin


class NetSales(Base, BaseMixin, BranchAwareMixin, CurrencyAwareMixin):
    __tablename__ = "net_sales"

    invoice_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="INV-YYYY-NNNN"
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    client_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=False
    )
    issue_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    total_before_vat: Mapped[float] = mapped_column(Float, default=0.0)
    vat_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(20), default="DRAFT", comment="DRAFT/ISSUED/PAID/CANCELLED"
    )
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class NetPurchase(Base, BaseMixin, BranchAwareMixin, CurrencyAwareMixin):
    __tablename__ = "net_purchases"

    purchase_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="PUR-YYYY-NNNN"
    )
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    issue_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    total_before_vat: Mapped[float] = mapped_column(Float, default=0.0)
    vat_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(500), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)


class BankReconciliation(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "bank_reconciliations"

    session_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
    bank_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    statement_balance: Mapped[float] = mapped_column(Float, default=0.0)
    system_balance: Mapped[float] = mapped_column(Float, default=0.0)
    difference: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="IN_PROGRESS")


class BankImportSession(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "bank_import_sessions"

    bank_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_transactions: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="IMPORTED")
    import_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


class BankStaging(Base, BaseMixin):
    __tablename__ = "bank_trnx_staging"

    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bank_import_sessions.id"), nullable=False
    )
    transaction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    debit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    credit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    reference: Mapped[str] = mapped_column(String(100), nullable=True)
    is_matched: Mapped[bool] = mapped_column(Boolean, default=False)


class BankUnmatched(Base, BaseMixin):
    __tablename__ = "bank_unmatched"

    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bank_import_sessions.id"), nullable=False
    )
    staging_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bank_trnx_staging.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class BankCurrencyMapping(Base, BaseMixin):
    __tablename__ = "bank_currency_mapping"

    bank_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    source_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    conversion_rate: Mapped[float] = mapped_column(Float, default=1.0)


class PettyCashReg(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "petty_cash_registers"

    register_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(20), default="OPEN", comment="OPEN/CLOSED/APPROVED"
    )
    approved_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    approval_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    lines = relationship("PettyCashLine", back_populates="register")


class PettyCashLine(Base, BaseMixin):
    __tablename__ = "petty_cash_lines"

    register_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("petty_cash_registers.id"), nullable=False
    )
    expense_category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    receipt_number: Mapped[str] = mapped_column(String(100), nullable=True)
    receipt_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    register = relationship("PettyCashReg", back_populates="lines")


class ChequeBook(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "cheque_books"

    bank_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    cheque_book_number: Mapped[str] = mapped_column(String(50), nullable=False)
    start_number: Mapped[int] = mapped_column(Integer, nullable=False)
    end_number: Mapped[int] = mapped_column(Integer, nullable=False)
    current_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    issue_date: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
