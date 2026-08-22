"""
Multi-Entity Consolidation Models
==================================
Supports: IFRS 10 (Consolidated Financial Statements),
          IAS 27 (Separate Financial Statements),
          IAS 28 (Investments in Associates),
          IFRS 3 (Business Combinations)

Key concepts:
  - Entity: Legal entity within the group
  - Ownership: Parent-subsidiary, associate, joint venture
  - Intercompany: Transactions, balances, unrealized profit
  - Consolidation: Full consolidation, equity method, proportional
  - Elimination: Automatic elimination of intercompany items
  - Translation: Foreign currency translation (IAS 21)
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


# ── Enums ──────────────────────────────────────────────────────────────


class EntityType(str, enum.Enum):
    SUBSIDIARY = "subsidiary"           # >50% ownership → full consolidation
    ASSOCIATE = "associate"             # 20-50% → equity method
    JOINT_VENTURE = "joint_venture"     # Joint control → proportional/equity
    PARENT = "parent"                   # The consolidating entity (holding)
    BRANCH = "branch"                   # Same legal entity, different location


class ConsolidationMethod(str, enum.Enum):
    FULL = "full"                       # 100% of assets/liabilities, minority interest
    EQUITY = "equity"                   # Single line: investment in associate
    PROPORTIONAL = "proportional"       # Pro-rata consolidation (joint ventures)
    COST = "cost"                       # At cost (no control/influence)


class EliminationType(str, enum.Enum):
    INTERCOMPANY_SALES = "intercompany_sales"         # IC revenue/COS elimination
    INTERCOMPANY_BALANCE = "intercompany_balance"     # IC receivables/payables
    INTERCOMPANY_DIVIDEND = "intercompany_dividend"   # IC dividend elimination
    UNREALIZED_PROFIT = "unrealized_profit"           # UP in inventory/fixed assets
    INVESTMENT_ELIMINATION = "investment_elimination" # Parent investment vs subsidiary equity
    GOODWILL = "goodwill"                             # Goodwill calculation and impairment


class ConsolidationStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    VALIDATED = "validated"
    APPROVED = "approved"
    POSTED = "posted"


# ── Models ─────────────────────────────────────────────────────────────


class Entity(Base, BaseMixin, BilingualMixin, AuditableMixin):
    """A legal entity within the group structure."""

    __tablename__ = "me_entities"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType), nullable=False, default=EntityType.SUBSIDIARY
    )
    registration_number: Mapped[str] = mapped_column(String(100), nullable=True)
    tax_id: Mapped[str] = mapped_column(String(50), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Egypt")
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False, default=1
    )
    functional_currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False, default=1
    )
    fiscal_year_end: Mapped[str] = mapped_column(String(5), default="12-31")
    consolidation_method: Mapped[ConsolidationMethod] = mapped_column(
        Enum(ConsolidationMethod), nullable=False, default=ConsolidationMethod.FULL
    )
    is_consolidating_entity: Mapped[bool] = mapped_column(Boolean, default=False)
    branch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("branches.id"), nullable=True
    )
    address: Mapped[str] = mapped_column(Text, nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Relationships
    ownerships_as_parent = relationship(
        "EntityOwnership", foreign_keys="EntityOwnership.parent_entity_id",
        back_populates="parent_entity"
    )
    ownerships_as_subsidiary = relationship(
        "EntityOwnership", foreign_keys="EntityOwnership.subsidiary_entity_id",
        back_populates="subsidiary_entity"
    )


class EntityOwnership(Base, BaseMixin, AuditableMixin):
    """Ownership structure: who owns what percentage of whom."""

    __tablename__ = "me_entity_ownerships"

    parent_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=False
    )
    subsidiary_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=False
    )
    ownership_pct: Mapped[float] = mapped_column(Float, nullable=False)
    voting_pct: Mapped[float] = mapped_column(Float, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    disposal_date: Mapped[date] = mapped_column(Date, nullable=True)
    goodwill_amount: Mapped[float] = mapped_column(Float, default=0.0)
    goodwill_currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=True
    )
    is_direct: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "parent_entity_id", "subsidiary_entity_id",
            name="uq_entity_ownership"
        ),
    )

    parent_entity = relationship(
        "Entity", foreign_keys=[parent_entity_id],
        back_populates="ownerships_as_parent"
    )
    subsidiary_entity = relationship(
        "Entity", foreign_keys=[subsidiary_entity_id],
        back_populates="ownerships_as_subsidiary"
    )


class IntercompanyTransaction(Base, BaseMixin, AuditableMixin):
    """Transaction between two entities in the group."""

    __tablename__ = "me_intercompany_transactions"

    transaction_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=False
    )
    to_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=False
    )
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False, default=1
    )
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)
    amount_in_reporting_currency: Mapped[float] = mapped_column(Float, nullable=True)
    elimination_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )
    eliminated_in_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_consolidation_periods.id"), nullable=True
    )
    reference_document_type: Mapped[str] = mapped_column(String(50), nullable=True)
    reference_document_id: Mapped[int] = mapped_column(Integer, nullable=True)
    unrealized_profit: Mapped[float] = mapped_column(Float, default=0.0)
    profit_elimination_pct: Mapped[float] = mapped_column(Float, default=100.0)

    from_entity = relationship("Entity", foreign_keys=[from_entity_id])
    to_entity = relationship("Entity", foreign_keys=[to_entity_id])
    eliminated_in_period = relationship("ConsolidationPeriod")


class IntercompanyBalance(Base, BaseMixin, AuditableMixin):
    """End-of-period intercompany balances for elimination."""

    __tablename__ = "me_intercompany_balances"

    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=False
    )
    to_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=False
    )
    account_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False
    )
    balance_in_reporting_currency: Mapped[float] = mapped_column(Float, nullable=True)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False)
    difference: Mapped[float] = mapped_column(Float, default=0.0)
    period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_consolidation_periods.id"), nullable=True
    )


class ConsolidationPeriod(Base, BaseMixin):
    """A period for which consolidation is performed."""

    __tablename__ = "me_consolidation_periods"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    period_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly"
    )
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "fiscal_year", "period_number",
            name="uq_consolidation_period"
        ),
    )

    consolidation_runs = relationship(
        "ConsolidationRun", back_populates="period"
    )


class ConsolidationRun(Base, BaseMixin, AuditableMixin):
    """A specific execution of consolidation."""

    __tablename__ = "me_consolidation_runs"

    period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_consolidation_periods.id"), nullable=False
    )
    consolidating_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=False
    )
    run_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ConsolidationStatus] = mapped_column(
        Enum(ConsolidationStatus), default=ConsolidationStatus.DRAFT
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    approved_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    result_summary: Mapped[dict] = mapped_column(JSON, nullable=True)

    period = relationship("ConsolidationPeriod", back_populates="consolidation_runs")
    entries = relationship("ConsolidationEntry", back_populates="consolidation_run")
    eliminations = relationship("EliminationEntry", back_populates="consolidation_run")


class ConsolidationEntry(Base, BaseMixin, AuditableMixin):
    """Manual consolidation adjustment journal entry."""

    __tablename__ = "me_consolidation_entries"

    consolidation_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_consolidation_runs.id"), nullable=False
    )
    entry_number: Mapped[str] = mapped_column(String(50), nullable=False)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=True
    )
    debit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    credit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False, default=1
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    adjustment_type: Mapped[str] = mapped_column(
        String(50), nullable=True
    )

    consolidation_run = relationship(
        "ConsolidationRun", back_populates="entries"
    )


class EliminationEntry(Base, BaseMixin, AuditableMixin):
    """Auto-generated intercompany elimination entry."""

    __tablename__ = "me_elimination_entries"

    consolidation_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_consolidation_runs.id"), nullable=False
    )
    elimination_type: Mapped[EliminationType] = mapped_column(
        Enum(EliminationType), nullable=False
    )
    from_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=True
    )
    to_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_entities.id"), nullable=True
    )
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    debit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    credit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=True)
    reference_transaction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_intercompany_transactions.id"), nullable=True
    )
    is_auto_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    is_reversed: Mapped[bool] = mapped_column(Boolean, default=False)

    consolidation_run = relationship(
        "ConsolidationRun", back_populates="eliminations"
    )


class CurrencyTranslationRate(Base, BaseMixin):
    """Exchange rates used for consolidation translation (IAS 21)."""

    __tablename__ = "me_currency_translation_rates"

    from_currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False
    )
    to_currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False
    )
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    spot_rate: Mapped[float] = mapped_column(Float, nullable=False)
    average_rate: Mapped[float] = mapped_column(Float, nullable=True)
    closing_rate: Mapped[float] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")

    __table_args__ = (
        UniqueConstraint(
            "from_currency_id", "to_currency_id", "rate_date",
            name="uq_currency_translation_rate"
        ),
    )


class ConsolidatedReport(Base, BaseMixin, AuditableMixin):
    """Generated consolidated financial statements."""

    __tablename__ = "me_consolidated_reports"

    consolidation_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("me_consolidation_runs.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    report_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    reporting_currency_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("currencies.id"), nullable=False
    )
    total_assets: Mapped[float] = mapped_column(Float, default=0.0)
    total_liabilities: Mapped[float] = mapped_column(Float, default=0.0)
    total_equity: Mapped[float] = mapped_column(Float, default=0.0)
    minority_interest: Mapped[float] = mapped_column(Float, default=0.0)
    net_income: Mapped[float] = mapped_column(Float, default=0.0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
