"""Financial Value-Based Strategy — SQLAlchemy models for historical tracking."""

from sqlalchemy import String, Float, Boolean, Integer, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import BaseMixin


class EVARecord(Base, BaseMixin):
    __tablename__ = "financial_eva_records"

    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    nopat: Mapped[float] = mapped_column(Float, nullable=False)
    capital_employed: Mapped[float] = mapped_column(Float, nullable=False)
    wacc_pct: Mapped[float] = mapped_column(Float, nullable=False)
    capital_charge: Mapped[float] = mapped_column(Float, nullable=False)
    eva: Mapped[float] = mapped_column(Float, nullable=False)
    value_created: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ann_predicted_eva: Mapped[float | None] = mapped_column(Float, nullable=True)
    ann_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EBITDARecord(Base, BaseMixin):
    __tablename__ = "financial_ebitda_records"

    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    revenue: Mapped[float] = mapped_column(Float, nullable=False)
    cogs: Mapped[float] = mapped_column(Float, nullable=False)
    opex: Mapped[float] = mapped_column(Float, nullable=False)
    depreciation: Mapped[float] = mapped_column(Float, nullable=False)
    gross_profit: Mapped[float] = mapped_column(Float, nullable=False)
    ebitda: Mapped[float] = mapped_column(Float, nullable=False)
    gross_margin_pct: Mapped[float] = mapped_column(Float, nullable=False)
    ebitda_margin_pct: Mapped[float] = mapped_column(Float, nullable=False)
    ann_predicted_ebitda: Mapped[float | None] = mapped_column(Float, nullable=True)
    ann_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class DCFValuation(Base, BaseMixin):
    __tablename__ = "financial_dcf_valuations"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    discount_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    terminal_growth_pct: Mapped[float] = mapped_column(Float, nullable=False)
    cash_flows: Mapped[dict | None] = mapped_column(JSON, nullable=False)
    pv_fcf: Mapped[dict | None] = mapped_column(JSON, nullable=False)
    total_pv_fcf: Mapped[float] = mapped_column(Float, nullable=False)
    terminal_value: Mapped[float] = mapped_column(Float, nullable=False)
    pv_terminal: Mapped[float] = mapped_column(Float, nullable=False)
    enterprise_value: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResidualIncomeRecord(Base, BaseMixin):
    __tablename__ = "financial_residual_income_records"

    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    net_income: Mapped[float] = mapped_column(Float, nullable=False)
    equity_book_value: Mapped[float] = mapped_column(Float, nullable=False)
    cost_of_equity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    cost_of_equity_charge: Mapped[float] = mapped_column(Float, nullable=False)
    residual_income: Mapped[float] = mapped_column(Float, nullable=False)
    value_created: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class EconomicProfitRecord(Base, BaseMixin):
    __tablename__ = "financial_economic_profit_records"

    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    invested_capital: Mapped[float] = mapped_column(Float, nullable=False)
    roic_pct: Mapped[float] = mapped_column(Float, nullable=False)
    wacc_pct: Mapped[float] = mapped_column(Float, nullable=False)
    spread_pct: Mapped[float] = mapped_column(Float, nullable=False)
    economic_profit: Mapped[float] = mapped_column(Float, nullable=False)
    value_created: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MVARecord(Base, BaseMixin):
    __tablename__ = "financial_mva_records"

    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    market_value: Mapped[float] = mapped_column(Float, nullable=False)
    invested_capital: Mapped[float] = mapped_column(Float, nullable=False)
    mva: Mapped[float] = mapped_column(Float, nullable=False)
    value_created: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TSRRecord(Base, BaseMixin):
    __tablename__ = "financial_tsr_records"

    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    beginning_price: Mapped[float] = mapped_column(Float, nullable=False)
    ending_price: Mapped[float] = mapped_column(Float, nullable=False)
    dividends_paid: Mapped[float] = mapped_column(Float, nullable=False)
    holding_period_years: Mapped[int] = mapped_column(Integer, nullable=False)
    capital_gain: Mapped[float] = mapped_column(Float, nullable=False)
    capital_gain_yield_pct: Mapped[float] = mapped_column(Float, nullable=False)
    dividend_yield_pct: Mapped[float] = mapped_column(Float, nullable=False)
    total_return_pct: Mapped[float] = mapped_column(Float, nullable=False)
    annualized_tsr_pct: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class FCFRecord(Base, BaseMixin):
    __tablename__ = "financial_fcf_records"

    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    operating_cash_flow: Mapped[float] = mapped_column(Float, nullable=False)
    capex: Mapped[float] = mapped_column(Float, nullable=False)
    interest_expense: Mapped[float] = mapped_column(Float, nullable=False)
    tax_rate_pct: Mapped[float] = mapped_column(Float, nullable=False)
    after_tax_interest: Mapped[float] = mapped_column(Float, nullable=False)
    free_cash_flow: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
