"""
FAR-GL Models — Financial Accounting & Reporting: General Ledger
=================================================================
Supports: Fiscal periods, chart of accounts, journal posting,
          trial balance, adjusting entries, year-end close,
          financial reports (balance sheet, P&L).
"""

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Integer, String, Float, ForeignKey, DateTime, Boolean,
    Date, Text, Enum, Numeric, UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base
from app.models.base import BaseMixin, BilingualMixin, AuditableMixin
from app.models.base import _utcnow


class PeriodStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"


class JournalStatus(str, enum.Enum):
    DRAFT = "draft"
    POSTED = "posted"
    REVERSED = "reversed"


class AdjustingEntryType(str, enum.Enum):
    ACCRUAL = "accrual"
    DEFERRAL = "deferral"
    DEPRECIATION = "depreciation"
    PROVISION = "provision"
    REVALUATION = "revaluation"
    CORRECTION = "correction"
    OTHER = "other"


class AdjustingEntryStatus(str, enum.Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    POSTED = "posted"


class NormalBalance(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class AccountType(str, enum.Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class AccountCategory(str, enum.Enum):
    CURRENT_ASSET = "current_asset"
    NON_CURRENT_ASSET = "non_current_asset"
    CURRENT_LIABILITY = "current_liability"
    NON_CURRENT_LIABILITY = "non_current_liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    COGS = "cogs"
    OPEX = "opex"
    OTHER = "other"


class YearEndStage(str, enum.Enum):
    PRE_CLOSE_CHECK = "pre_close_check"
    ADJUSTING_ENTRIES = "adjusting_entries"
    DEPRECIATION = "depreciation"
    AMORTIZATION = "amortization"
    INVENTORY_VALUATION = "inventory_valuation"
    ACCRUALS = "accruals"
    DEFERRALS = "deferrals"
    TAX_PROVISIONS = "tax_provisions"
    FINAL_TRIAL_BALANCE = "final_trial_balance"
    CLOSE_INCOME = "close_income"
    CLOSE_DIVIDENDS = "close_dividends"
    POST_CLOSE_TB = "post_close_tb"
    LOCK_PERIOD = "lock_period"


class GLPeriod(Base, BaseMixin):
    """Fiscal period within a financial year."""

    __tablename__ = "gl_periods"

    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[PeriodStatus] = mapped_column(
        Enum(PeriodStatus), nullable=False, default=PeriodStatus.OPEN
    )
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    locked_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    locked_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    is_adjustment_period: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year", "period_number", name="uq_gl_period"
        ),
    )

    journals = relationship("GLJournal", back_populates="period")
    trial_balances = relationship("GLTrialBalance", back_populates="period")
    adjusting_entries = relationship("GLAdjustingEntry", back_populates="period")


class GLAccount(Base, BaseMixin, BilingualMixin):
    """Chart of accounts — hierarchical account structure."""

    __tablename__ = "gl_accounts"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType), nullable=False
    )
    normal_balance: Mapped[NormalBalance] = mapped_column(
        Enum(NormalBalance), nullable=False
    )
    category: Mapped[AccountCategory] = mapped_column(
        Enum(AccountCategory), nullable=False, default=AccountCategory.OTHER
    )
    is_control: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_accounts.id"), nullable=True
    )
    level: Mapped[int] = mapped_column(Integer, default=0)
    is_bank_account: Mapped[bool] = mapped_column(Boolean, default=False)
    is_tax_account: Mapped[bool] = mapped_column(Boolean, default=False)
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False, default=1
    )
    exchange_rate_type: Mapped[str] = mapped_column(String(20), nullable=True)
    vat_rate: Mapped[float] = mapped_column(Float, default=0.0)
    vat_type: Mapped[str] = mapped_column(String(20), nullable=True)
    allow_manual_entry: Mapped[bool] = mapped_column(Boolean, default=True)
    reconciliation_required: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    parent = relationship("GLAccount", remote_side="GLAccount.id", backref="children")
    journal_lines = relationship("GLJournalLine", back_populates="account")
    tb_records = relationship("GLTrialBalance", back_populates="account")


class GLJournal(Base, BaseMixin, AuditableMixin):
    """Journal entry header."""

    __tablename__ = "gl_journals"

    journal_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_periods.id"), nullable=False
    )
    journal_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[JournalStatus] = mapped_column(
        Enum(JournalStatus), nullable=False, default=JournalStatus.DRAFT
    )
    total_debit: Mapped[float] = mapped_column(Float, default=0.0)
    total_credit: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    reference_type: Mapped[str] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[int] = mapped_column(Integer, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    posted_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    reversed_journal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_journals.id"), nullable=True
    )
    reversal_date: Mapped[date] = mapped_column(Date, nullable=True)
    is_adjusting: Mapped[bool] = mapped_column(Boolean, default=False)
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=True
    )
    entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=True
    )

    period = relationship("GLPeriod", back_populates="journals")
    lines = relationship(
        "GLJournalLine", back_populates="journal",
        cascade="all, delete-orphan",
        order_by="GLJournalLine.id"
    )
    reversed_journal = relationship("GLJournal", remote_side="GLJournal.id")


class GLJournalLine(Base, BaseMixin):
    """Individual line in a journal entry."""

    __tablename__ = "gl_journal_lines"

    journal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_journals.id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_accounts.id"), nullable=False
    )
    line_description: Mapped[str] = mapped_column(Text, nullable=True)
    debit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    credit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False, default=1
    )
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)
    base_amount: Mapped[float] = mapped_column(Float, nullable=True)
    cost_center_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cost_centers.id"), nullable=True
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=True
    )
    entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=True
    )

    journal = relationship("GLJournal", back_populates="lines")
    account = relationship("GLAccount", back_populates="journal_lines")


class GLTrialBalance(Base, BaseMixin):
    """Period-end trial balance for each account."""

    __tablename__ = "gl_trial_balances"

    period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_periods.id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_accounts.id"), nullable=False
    )
    opening_debit: Mapped[float] = mapped_column(Float, default=0.0)
    opening_credit: Mapped[float] = mapped_column(Float, default=0.0)
    debit_turnover: Mapped[float] = mapped_column(Float, default=0.0)
    credit_turnover: Mapped[float] = mapped_column(Float, default=0.0)
    closing_debit: Mapped[float] = mapped_column(Float, default=0.0)
    closing_credit: Mapped[float] = mapped_column(Float, default=0.0)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint(
            "period_id", "account_id", name="uq_gl_trial_balance"
        ),
    )

    period = relationship("GLPeriod", back_populates="trial_balances")
    account = relationship("GLAccount", back_populates="tb_records")


class GLAdjustingEntry(Base, BaseMixin, AuditableMixin):
    """Adjusting journal entry for end-of-period corrections."""

    __tablename__ = "gl_adjusting_entries"

    entry_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_periods.id"), nullable=False
    )
    entry_type: Mapped[AdjustingEntryType] = mapped_column(
        Enum(AdjustingEntryType), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[AdjustingEntryStatus] = mapped_column(
        Enum(AdjustingEntryStatus), nullable=False, default=AdjustingEntryStatus.DRAFT
    )
    total_debit: Mapped[float] = mapped_column(Float, default=0.0)
    total_credit: Mapped[float] = mapped_column(Float, default=0.0)
    journal_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_journals.id"), nullable=True
    )
    approved_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    period = relationship("GLPeriod", back_populates="adjusting_entries")
    journal = relationship("GLJournal")
    lines = relationship(
        "GLAdjustingEntryLine", back_populates="entry",
        cascade="all, delete-orphan"
    )


class GLAdjustingEntryLine(Base, BaseMixin):
    """Line in an adjusting entry."""

    __tablename__ = "gl_adjusting_entry_lines"

    adjusting_entry_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_adjusting_entries.id"), nullable=False
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_accounts.id"), nullable=False
    )
    line_description: Mapped[str] = mapped_column(Text, nullable=True)
    debit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    credit_amount: Mapped[float] = mapped_column(Float, default=0.0)

    entry = relationship("GLAdjustingEntry", back_populates="lines")
    account = relationship("GLAccount")


class GLYearEndClose(Base, BaseMixin, AuditableMixin):
    """Year-end closing process tracking."""

    __tablename__ = "gl_year_end_closes"

    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    stages_completed: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)
    closing_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_periods.id"), nullable=False
    )
    opening_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_periods.id"), nullable=False
    )
    income_summary_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_accounts.id"), nullable=False
    )
    retained_earnings_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("gl_accounts.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    total_revenue: Mapped[float] = mapped_column(Float, default=0.0)
    total_expenses: Mapped[float] = mapped_column(Float, default=0.0)
    net_income: Mapped[float] = mapped_column(Float, default=0.0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year", name="uq_gl_year_end_close"
        ),
    )
