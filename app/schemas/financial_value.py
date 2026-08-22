"""Financial Value-Based Strategy — Pydantic schemas for requests and responses."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ── Request Schemas ──────────────────────────────────────────────────


class EVARequest(BaseModel):
    nopat: float = Field(..., description="Net Operating Profit After Tax")
    capital_employed: float = Field(..., gt=0)
    wacc_pct: float = Field(..., ge=0, le=100, description="Weighted Average Cost of Capital (%)")
    period: str = Field(default="2026-Q1", pattern=r"^\d{4}-Q[1-4]$|^\d{4}-\d{2}$")
    notes: Optional[str] = None


class EBITDARequest(BaseModel):
    revenue: float = Field(..., gt=0)
    cogs: float = Field(..., ge=0)
    opex: float = Field(..., ge=0)
    da: float = Field(..., ge=0, description="Depreciation & Amortization")
    period: str = Field(default="2026-Q1", pattern=r"^\d{4}-Q[1-4]$|^\d{4}-\d{2}$")
    notes: Optional[str] = None


class DCFRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    cash_flows: List[float] = Field(..., min_length=1)
    discount_rate_pct: float = Field(..., gt=0, le=100)
    terminal_growth_pct: float = Field(default=2.0, ge=-5, le=20)
    projection_years: int = Field(default=5, ge=1, le=30)
    notes: Optional[str] = None


class ResidualIncomeRequest(BaseModel):
    net_income: float
    equity_book_value: float = Field(..., gt=0)
    cost_of_equity_pct: float = Field(..., ge=0, le=100)
    period: str = Field(default="2026-Q1", pattern=r"^\d{4}-Q[1-4]$|^\d{4}-\d{2}$")
    notes: Optional[str] = None


class EconomicProfitRequest(BaseModel):
    invested_capital: float = Field(..., gt=0)
    roic_pct: float = Field(..., description="Return on Invested Capital (%)")
    wacc_pct: float = Field(..., ge=0, le=100)
    period: str = Field(default="2026-Q1", pattern=r"^\d{4}-Q[1-4]$|^\d{4}-\d{2}$")
    notes: Optional[str] = None


class MVARequest(BaseModel):
    market_value: float = Field(..., gt=0)
    invested_capital: float = Field(..., gt=0)
    period: str = Field(default="2026-Q1", pattern=r"^\d{4}-Q[1-4]$|^\d{4}-\d{2}$")
    notes: Optional[str] = None


class TSRRequest(BaseModel):
    beginning_price: float = Field(..., gt=0)
    ending_price: float = Field(..., gt=0)
    dividends_paid: float = Field(default=0.0, ge=0)
    holding_period_years: int = Field(default=1, ge=1, le=30)
    period: str = Field(default="2026-Q1", pattern=r"^\d{4}-Q[1-4]$|^\d{4}-\d{2}$")
    notes: Optional[str] = None


class FCFRequest(BaseModel):
    operating_cash_flow: float
    capex: float = Field(..., ge=0)
    interest_expense: float = Field(default=0.0, ge=0)
    tax_rate_pct: float = Field(default=25.0, ge=0, le=100)
    period: str = Field(default="2026-Q1", pattern=r"^\d{4}-Q[1-4]$|^\d{4}-\d{2}$")
    notes: Optional[str] = None


# ── Response Schemas ─────────────────────────────────────────────────


class EVAResponse(BaseModel):
    success: bool = True
    record_id: Optional[int] = None
    period: str
    nopat: float
    capital_employed: float
    wacc_pct: float
    capital_charge: float
    eva: float
    value_created: bool
    ann_predicted_eva: Optional[float] = None
    ann_confidence: Optional[float] = None
    model_version: str = "1.0-heuristic"
    timestamp: str


class EBITDAResponse(BaseModel):
    success: bool = True
    record_id: Optional[int] = None
    period: str
    revenue: float
    gross_profit: float
    ebitda: float
    gross_margin_pct: float
    ebitda_margin_pct: float
    ann_predicted_ebitda: Optional[float] = None
    ann_confidence: Optional[float] = None
    model_version: str = "1.0-heuristic"
    timestamp: str


class DCFResponse(BaseModel):
    success: bool = True
    record_id: Optional[int] = None
    company_name: str
    pv_fcf: List[float]
    total_pv_fcf: float
    terminal_value: float
    pv_terminal: float
    enterprise_value: float
    timestamp: str


class ResidualIncomeResponse(BaseModel):
    success: bool = True
    record_id: Optional[int] = None
    period: str
    net_income: float
    equity_book_value: float
    cost_of_equity_pct: float
    cost_of_equity_charge: float
    residual_income: float
    value_created: bool
    timestamp: str


class EconomicProfitResponse(BaseModel):
    success: bool = True
    record_id: Optional[int] = None
    period: str
    invested_capital: float
    roic_pct: float
    wacc_pct: float
    spread_pct: float
    economic_profit: float
    value_created: bool
    timestamp: str


class MVAResponse(BaseModel):
    success: bool = True
    record_id: Optional[int] = None
    period: str
    market_value: float
    invested_capital: float
    mva: float
    value_created: bool
    timestamp: str


class TSRResponse(BaseModel):
    success: bool = True
    record_id: Optional[int] = None
    period: str
    capital_gain: float
    capital_gain_yield_pct: float
    dividend_yield_pct: float
    total_return_pct: float
    annualized_tsr_pct: float
    timestamp: str


class FCFResponse(BaseModel):
    success: bool = True
    record_id: Optional[int] = None
    period: str
    operating_cash_flow: float
    capex: float
    after_tax_interest: float
    free_cash_flow: float
    timestamp: str


# ── History / Query Schemas ──────────────────────────────────────────


class FinancialRecordResponse(BaseModel):
    id: int
    period: str
    created_at: str
    is_active: bool
    data: Dict[str, Any]


class FinancialHistoryResponse(BaseModel):
    success: bool = True
    record_type: str
    total: int
    records: List[FinancialRecordResponse]
