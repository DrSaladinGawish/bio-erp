"""
Multi-Entity Consolidation Pydantic Schemas
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ── Entity ─────────────────────────────────────────────────────────────

class EntityCreate(BaseModel):
    code: str
    name_en: str
    name_ar: Optional[str] = None
    entity_type: str = "subsidiary"
    registration_number: Optional[str] = None
    tax_id: Optional[str] = None
    country: str = "Egypt"
    currency_id: int = 1
    functional_currency_id: int = 1
    fiscal_year_end: str = "12-31"
    consolidation_method: str = "full"
    is_consolidating_entity: bool = False
    branch_id: Optional[int] = None
    address: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class EntityResponse(BaseModel):
    id: int
    code: str
    name_en: str
    name_ar: Optional[str] = None
    entity_type: str
    country: str
    currency_id: int
    consolidation_method: str
    is_consolidating_entity: bool
    is_active: bool
    created_at: datetime


# ── Ownership ──────────────────────────────────────────────────────────

class OwnershipCreate(BaseModel):
    parent_entity_id: int
    subsidiary_entity_id: int
    ownership_pct: float = Field(..., gt=0, le=100)
    voting_pct: Optional[float] = None
    effective_date: date
    disposal_date: Optional[date] = None
    goodwill_amount: float = 0.0
    goodwill_currency_id: Optional[int] = None
    is_direct: bool = True
    notes: Optional[str] = None


class OwnershipResponse(BaseModel):
    id: int
    parent_entity_id: int
    subsidiary_entity_id: int
    ownership_pct: float
    effective_date: date
    disposal_date: Optional[date] = None
    is_direct: bool


# ── Intercompany Transaction ───────────────────────────────────────────

class ICTransactionCreate(BaseModel):
    transaction_number: str
    transaction_date: date
    from_entity_id: int
    to_entity_id: int
    transaction_type: str
    description: Optional[str] = None
    amount: float
    currency_id: int = 1
    exchange_rate: float = 1.0
    reference_document_type: Optional[str] = None
    reference_document_id: Optional[int] = None
    unrealized_profit: float = 0.0
    profit_elimination_pct: float = 100.0


class ICTransactionResponse(BaseModel):
    id: int
    transaction_number: str
    transaction_date: date
    from_entity_id: int
    to_entity_id: int
    transaction_type: str
    amount: float
    currency_id: int
    elimination_status: str
    created_at: datetime


# ── Consolidation Period ───────────────────────────────────────────────

class PeriodCreate(BaseModel):
    name: str
    period_type: str = "monthly"
    fiscal_year: int
    period_number: int
    start_date: date
    end_date: date


class PeriodResponse(BaseModel):
    id: int
    name: str
    fiscal_year: int
    period_number: int
    start_date: date
    end_date: date
    is_closed: bool


# ── Consolidation Run ──────────────────────────────────────────────────

class ConsolidationRunCreate(BaseModel):
    period_id: int
    consolidating_entity_id: int
    notes: Optional[str] = None


class ConsolidationRunResponse(BaseModel):
    id: int
    period_id: int
    consolidating_entity_id: int
    run_number: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class ConsolidationRunDetail(BaseModel):
    id: int
    period: PeriodResponse
    status: str
    entries_count: int = 0
    eliminations_count: int = 0
    total_debits: float = 0.0
    total_credits: float = 0.0


# ── Elimination ────────────────────────────────────────────────────────

class EliminationEntryCreate(BaseModel):
    consolidation_run_id: int
    elimination_type: str
    from_entity_id: Optional[int] = None
    to_entity_id: Optional[int] = None
    account_id: int
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    currency_id: int = 1
    description: Optional[str] = None
    reference_transaction_id: Optional[int] = None


class EliminationEntryResponse(BaseModel):
    id: int
    consolidation_run_id: int
    elimination_type: str
    debit_amount: float
    credit_amount: float
    description: Optional[str] = None
    is_auto_generated: bool


# ── Currency Translation ───────────────────────────────────────────────

class TranslationRateCreate(BaseModel):
    from_currency_id: int
    to_currency_id: int
    rate_date: date
    spot_rate: float
    average_rate: Optional[float] = None
    closing_rate: Optional[float] = None
    source: str = "manual"


class TranslationRateResponse(BaseModel):
    id: int
    from_currency_id: int
    to_currency_id: int
    rate_date: date
    spot_rate: float
    closing_rate: Optional[float] = None


# ── Consolidated Report ────────────────────────────────────────────────

class ReportResponse(BaseModel):
    id: int
    consolidation_run_id: int
    report_type: str
    total_assets: float
    total_liabilities: float
    total_equity: float
    minority_interest: float
    net_income: float
    generated_at: datetime


class BalanceSheetLine(BaseModel):
    account_code: str
    account_name: str
    entity_name: Optional[str] = None
    balance: float
    consolidated_balance: float
    elimination_amount: float = 0.0


class ConsolidatedBalanceSheet(BaseModel):
    report_type: str = "balance_sheet"
    as_of_date: date
    reporting_currency: str
    lines: List[BalanceSheetLine]
    total_assets: float
    total_liabilities: float
    total_equity: float
    minority_interest: float
    check: str  # Assets = Liabilities + Equity
