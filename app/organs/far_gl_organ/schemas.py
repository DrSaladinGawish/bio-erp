"""
FAR-GL Pydantic Schemas — Request/Response models for all 25+ endpoints.
"""

from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ── Periods ───────────────────────────────────────────────────────────

class PeriodCreate(BaseModel):
    fiscal_year: int = Field(..., ge=2000, le=2100)
    period_number: int = Field(..., ge=1, le=13)
    name: str
    start_date: date
    end_date: date
    is_adjustment_period: bool = False
    notes: Optional[str] = None


class PeriodResponse(BaseModel):
    id: int
    fiscal_year: int
    period_number: int
    name: str
    start_date: date
    end_date: date
    status: str
    is_adjustment_period: bool
    is_active: bool
    created_at: datetime


class PeriodListResponse(BaseModel):
    periods: List[PeriodResponse]
    total: int


# ── Accounts ──────────────────────────────────────────────────────────

class AccountCreate(BaseModel):
    code: str
    name_en: str
    name_ar: Optional[str] = None
    account_type: str
    normal_balance: str = "debit"
    category: str = "other"
    is_control: bool = False
    parent_id: Optional[int] = None
    level: int = 0
    is_bank_account: bool = False
    is_tax_account: bool = False
    currency_id: int = 1
    vat_rate: float = 0.0
    vat_type: Optional[str] = None
    allow_manual_entry: bool = True
    reconciliation_required: bool = False
    notes: Optional[str] = None


class AccountUpdate(BaseModel):
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    is_active: Optional[bool] = None
    parent_id: Optional[int] = None
    allow_manual_entry: Optional[bool] = None
    reconciliation_required: Optional[bool] = None
    notes: Optional[str] = None


class AccountResponse(BaseModel):
    id: int
    code: str
    name_en: str
    name_ar: Optional[str] = None
    account_type: str
    normal_balance: str
    category: str
    is_control: bool
    parent_id: Optional[int] = None
    level: int
    is_active: bool
    allow_manual_entry: bool
    created_at: datetime
    children_count: int = 0


class AccountTreeNode(BaseModel):
    id: int
    code: str
    name_en: str
    account_type: str
    normal_balance: str
    level: int
    is_control: bool
    is_active: bool
    children: List["AccountTreeNode"] = []


class COATemplateGenerate(BaseModel):
    template_name: str
    fiscal_year: int = 2026


# ── Journals ──────────────────────────────────────────────────────────

class JournalLineCreate(BaseModel):
    account_id: int
    line_description: Optional[str] = None
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    currency_id: int = 1
    exchange_rate: float = 1.0
    cost_center_id: Optional[int] = None
    project_id: Optional[int] = None
    branch_id: Optional[int] = None
    entity_id: Optional[int] = None


class JournalCreate(BaseModel):
    period_id: int
    journal_date: date
    description: Optional[str] = None
    source: str = "manual"
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    is_adjusting: bool = False
    branch_id: Optional[int] = None
    entity_id: Optional[int] = None
    lines: List[JournalLineCreate] = Field(..., min_length=2)


class JournalLineResponse(BaseModel):
    id: int
    account_id: int
    account_code: str = ""
    account_name: str = ""
    line_description: Optional[str] = None
    debit_amount: float
    credit_amount: float
    currency_id: int


class JournalResponse(BaseModel):
    id: int
    journal_number: str
    period_id: int
    journal_date: date
    description: Optional[str] = None
    status: str
    total_debit: float
    total_credit: float
    source: str
    posted_at: Optional[datetime] = None
    is_adjusting: bool
    created_at: datetime
    lines: List[JournalLineResponse] = []


class JournalListResponse(BaseModel):
    journals: List[JournalResponse]
    total: int
    page: int = 1
    page_size: int = 20


class JournalReverse(BaseModel):
    reversal_date: date
    description: Optional[str] = None


# ── Trial Balance ─────────────────────────────────────────────────────

class TrialBalanceLine(BaseModel):
    account_id: int
    account_code: str
    account_name: str
    account_type: str
    opening_debit: float
    opening_credit: float
    debit_turnover: float
    credit_turnover: float
    closing_debit: float
    closing_credit: float


class TrialBalanceResponse(BaseModel):
    period_id: int
    period_name: str
    fiscal_year: int
    period_number: int
    lines: List[TrialBalanceLine]
    total_debit: float
    total_credit: float
    is_balanced: bool
    difference: float
    calculated_at: datetime


class TrialBalanceValidate(BaseModel):
    period_id: int
    is_validated: bool


# ── Adjusting Entries ────────────────────────────────────────────────

class AdjustingEntryLineCreate(BaseModel):
    account_id: int
    line_description: Optional[str] = None
    debit_amount: float = 0.0
    credit_amount: float = 0.0


class AdjustingEntryCreate(BaseModel):
    period_id: int
    entry_type: str
    description: Optional[str] = None
    notes: Optional[str] = None
    lines: List[AdjustingEntryLineCreate] = Field(..., min_length=2)


class AdjustingEntryLineResponse(BaseModel):
    id: int
    account_id: int
    account_code: str = ""
    account_name: str = ""
    line_description: Optional[str] = None
    debit_amount: float
    credit_amount: float


class AdjustingEntryResponse(BaseModel):
    id: int
    entry_number: str
    period_id: int
    entry_type: str
    description: Optional[str] = None
    status: str
    total_debit: float
    total_credit: float
    approved_by: Optional[int] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    lines: List[AdjustingEntryLineResponse] = []


# ── Financial Reports ────────────────────────────────────────────────

class BalanceSheetLine(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    category: str
    balance: float
    is_control: bool
    level: int


class BalanceSheetResponse(BaseModel):
    period_id: int
    period_name: str
    as_of_date: date
    lines: List[BalanceSheetLine]
    total_assets: float
    total_liabilities: float
    total_equity: float
    check: str


class ProfitLossLine(BaseModel):
    account_code: str
    account_name: str
    account_type: str
    balance: float
    category: str


class ProfitLossResponse(BaseModel):
    period_id: int
    period_name: str
    start_date: date
    end_date: date
    lines: List[ProfitLossLine]
    total_revenue: float
    total_cogs: float
    gross_profit: float
    total_opex: float
    net_income: float
    check: str


# ── Year-End Close ────────────────────────────────────────────────────

class YearEndCloseStart(BaseModel):
    fiscal_year: int
    closing_period_id: int
    opening_period_id: int
    income_summary_account_id: int
    retained_earnings_account_id: int
    notes: Optional[str] = None


class YearEndStageComplete(BaseModel):
    stage: str
    notes: Optional[str] = None


class YearEndCloseResponse(BaseModel):
    id: int
    fiscal_year: int
    status: str
    stages_completed: Dict[str, Any]
    closing_period_id: int
    opening_period_id: int
    total_revenue: float
    total_expenses: float
    net_income: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


# ── Health ────────────────────────────────────────────────────────────

class HealthMetric(BaseModel):
    name: str
    status: str
    value: Any
    details: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    module: str = "far-gl"
    version: str = "1.0.0"
    metrics: List[HealthMetric] = []


# ── Generic ───────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
    id: Optional[int] = None


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
