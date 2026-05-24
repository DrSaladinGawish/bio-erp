from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel


class BudgetPeriodCreate(BaseModel):
    fiscal_year: int
    quarter: int | None = None
    month: int | None = None
    label: str
    start_date: datetime
    end_date: datetime


class BudgetPeriodResponse(BudgetPeriodCreate):
    id: int
    is_closed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetLineCreate(BaseModel):
    cost_center_id: int
    coa_account_id: int
    budget_period_id: int
    branch_id: int = 1
    budgeted_amount: Decimal = 0
    notes: str | None = None


class BudgetLineResponse(BaseModel):
    id: int
    cost_center_id: int
    coa_account_id: int
    budget_period_id: int
    branch_id: int
    budgeted_amount: Decimal
    actual_amount: Decimal
    committed_amount: Decimal
    variance_amount: Decimal
    variance_percent: float
    notes: str | None
    created_at: datetime
    cost_center_name: str | None = None
    coa_account_name: str | None = None
    period_label: str | None = None

    model_config = {"from_attributes": True}


class BudgetLineBulkCreate(BaseModel):
    lines: list[BudgetLineCreate]


class VarianceReportRow(BaseModel):
    cost_center_id: int
    cost_center_name: str
    coa_account_id: int
    coa_account_name: str
    budgeted: Decimal
    actual: Decimal
    variance: Decimal
    variance_pct: float
    flag: str


class VarianceReportResponse(BaseModel):
    period_label: str
    branch_id: int
    total_budgeted: Decimal
    total_actual: Decimal
    total_variance: Decimal
    rows: list[VarianceReportRow]


class CostAllocationCreate(BaseModel):
    from_cost_center_id: int
    to_cost_center_id: int
    budget_period_id: int
    allocation_base: str
    rate_percent: float = 0.0
    amount: Decimal = 0


class CostAllocationResponse(CostAllocationCreate):
    id: int
    is_executed: bool
    executed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BranchProfitabilityRow(BaseModel):
    branch_id: int
    branch_name: str
    revenue: Decimal
    direct_costs: Decimal
    gross_profit: Decimal
    gross_margin_pct: float
    operating_expenses: Decimal
    net_profit: Decimal
    net_margin_pct: float
    budget_variance: Decimal
    event_count: int
