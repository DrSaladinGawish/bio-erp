"""Financial Value-Based Strategy — Service layer with ANN overlay.

All calculations are pure functions. DB persistence is handled by the router.
ANN predictions are fetched asynchronously when available.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_value import (
    EVARecord,
    EBITDARecord,
    DCFValuation,
    ResidualIncomeRecord,
    EconomicProfitRecord,
    MVARecord,
    TSRRecord,
    FCFRecord,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Pure Calculations ────────────────────────────────────────────────


def calc_eva(nopat: float, capital_employed: float, wacc_pct: float) -> dict[str, Any]:
    capital_charge = capital_employed * (wacc_pct / 100)
    eva = nopat - capital_charge
    return {
        "capital_charge": round(capital_charge, 2),
        "eva": round(eva, 2),
        "value_created": eva > 0,
    }


def calc_ebitda(revenue: float, cogs: float, opex: float, da: float) -> dict[str, Any]:
    gross_profit = revenue - cogs
    ebitda = gross_profit - opex + da
    gross_margin = (gross_profit / revenue * 100) if revenue else 0
    ebitda_margin = (ebitda / revenue * 100) if revenue else 0
    return {
        "gross_profit": round(gross_profit, 2),
        "ebitda": round(ebitda, 2),
        "gross_margin_pct": round(gross_margin, 2),
        "ebitda_margin_pct": round(ebitda_margin, 2),
    }


def calc_dcf(
    cash_flows: list[float],
    discount_rate_pct: float,
    terminal_growth_pct: float = 2.0,
) -> dict[str, Any]:
    discount_factor = 1 + (discount_rate_pct / 100)
    pv_fcf = []
    for i, cf in enumerate(cash_flows):
        pv = cf / (discount_factor ** (i + 1))
        pv_fcf.append(round(pv, 2))
    total_pv_fcf = sum(pv_fcf)

    terminal_fcf = cash_flows[-1] * (1 + terminal_growth_pct / 100)
    rate_diff = discount_rate_pct / 100 - terminal_growth_pct / 100
    terminal_value = (terminal_fcf / rate_diff) if rate_diff > 0 else 0
    pv_terminal = terminal_value / (discount_factor ** len(cash_flows))
    enterprise_value = total_pv_fcf + pv_terminal

    return {
        "pv_fcf": pv_fcf,
        "total_pv_fcf": round(total_pv_fcf, 2),
        "terminal_value": round(terminal_value, 2),
        "pv_terminal": round(pv_terminal, 2),
        "enterprise_value": round(enterprise_value, 2),
    }


def calc_residual_income(
    net_income: float, equity_book_value: float, cost_of_equity_pct: float
) -> dict[str, Any]:
    cost_of_equity_charge = equity_book_value * (cost_of_equity_pct / 100)
    residual_income = net_income - cost_of_equity_charge
    return {
        "cost_of_equity_charge": round(cost_of_equity_charge, 2),
        "residual_income": round(residual_income, 2),
        "value_created": residual_income > 0,
    }


def calc_economic_profit(
    invested_capital: float, roic_pct: float, wacc_pct: float
) -> dict[str, Any]:
    spread = roic_pct / 100 - wacc_pct / 100
    economic_profit = invested_capital * spread
    return {
        "spread_pct": round(spread * 100, 4),
        "economic_profit": round(economic_profit, 2),
        "value_created": economic_profit > 0,
    }


def calc_mva(market_value: float, invested_capital: float) -> dict[str, Any]:
    mva = market_value - invested_capital
    return {
        "mva": round(mva, 2),
        "value_created": mva > 0,
    }


def calc_tsr(
    beginning_price: float,
    ending_price: float,
    dividends_paid: float,
    holding_period_years: int,
) -> dict[str, Any]:
    capital_gain = ending_price - beginning_price
    capital_gain_yield = (capital_gain / beginning_price * 100) if beginning_price else 0
    dividend_yield = (dividends_paid / beginning_price * 100) if beginning_price else 0
    total_return = capital_gain_yield + dividend_yield
    annualized_tsr = (
        ((1 + total_return / 100) ** (1 / holding_period_years) - 1) * 100
        if holding_period_years > 0
        else 0
    )
    return {
        "capital_gain": round(capital_gain, 2),
        "capital_gain_yield_pct": round(capital_gain_yield, 2),
        "dividend_yield_pct": round(dividend_yield, 2),
        "total_return_pct": round(total_return, 2),
        "annualized_tsr_pct": round(annualized_tsr, 2),
    }


def calc_fcf(
    operating_cash_flow: float,
    capex: float,
    interest_expense: float,
    tax_rate_pct: float,
) -> dict[str, Any]:
    after_tax_interest = interest_expense * (1 - tax_rate_pct / 100)
    fcf = operating_cash_flow - capex + after_tax_interest
    return {
        "after_tax_interest": round(after_tax_interest, 2),
        "free_cash_flow": round(fcf, 2),
    }


# ── ANN Overlay ──────────────────────────────────────────────────────


async def _get_ann_prediction(
    db: AsyncSession, prediction_type: str, entity_id: str
) -> dict[str, Any] | None:
    """Try to get ANN prediction; return None on any failure."""
    try:
        from app.services.neural.ann_predictors import (
            predict_financial_ann,
            predict_revenue_ann,
        )

        if prediction_type == "financial_ann":
            result = await predict_financial_ann(db, entity_id)
        elif prediction_type == "revenue_forecast":
            result = await predict_revenue_ann(db, entity_id)
        else:
            return None

        if "error" not in result and result.get("method") == "neural_network":
            return result
    except Exception as e:
        logger.debug("ANN prediction unavailable: %s", e)
    return None


# ── DB Persistence ───────────────────────────────────────────────────


async def save_eva(db: AsyncSession, period: str, nopat: float, capital_employed: float,
                   wacc_pct: float, notes: str | None = None) -> EVARecord:
    result = calc_eva(nopat, capital_employed, wacc_pct)

    ann = await _get_ann_prediction(db, "financial_ann", f"eva:{period}")
    record = EVARecord(
        period=period, nopat=nopat, capital_employed=capital_employed,
        wacc_pct=wacc_pct, capital_charge=result["capital_charge"],
        eva=result["eva"], value_created=result["value_created"],
        ann_predicted_eva=ann.get("eva") if ann else None,
        ann_confidence=ann.get("confidence") if ann else None,
        notes=notes,
    )
    db.add(record)
    await db.flush()
    return record


async def save_ebitda(db: AsyncSession, period: str, revenue: float, cogs: float,
                      opex: float, da: float, notes: str | None = None) -> EBITDARecord:
    result = calc_ebitda(revenue, cogs, opex, da)

    ann = await _get_ann_prediction(db, "financial_ann", f"ebitda:{period}")
    record = EBITDARecord(
        period=period, revenue=revenue, cogs=cogs, opex=opex,
        depreciation=da, gross_profit=result["gross_profit"],
        ebitda=result["ebitda"], gross_margin_pct=result["gross_margin_pct"],
        ebitda_margin_pct=result["ebitda_margin_pct"],
        ann_predicted_ebitda=ann.get("ebitda") if ann else None,
        ann_confidence=ann.get("confidence") if ann else None,
        notes=notes,
    )
    db.add(record)
    await db.flush()
    return record


async def save_dcf(db: AsyncSession, company_name: str, cash_flows: list[float],
                   discount_rate_pct: float, terminal_growth_pct: float,
                   notes: str | None = None) -> DCFValuation:
    result = calc_dcf(cash_flows, discount_rate_pct, terminal_growth_pct)
    record = DCFValuation(
        company_name=company_name, discount_rate_pct=discount_rate_pct,
        terminal_growth_pct=terminal_growth_pct, cash_flows=cash_flows,
        pv_fcf=result["pv_fcf"], total_pv_fcf=result["total_pv_fcf"],
        terminal_value=result["terminal_value"], pv_terminal=result["pv_terminal"],
        enterprise_value=result["enterprise_value"], notes=notes,
    )
    db.add(record)
    await db.flush()
    return record


async def save_residual_income(db: AsyncSession, period: str, net_income: float,
                               equity_book_value: float, cost_of_equity_pct: float,
                               notes: str | None = None) -> ResidualIncomeRecord:
    result = calc_residual_income(net_income, equity_book_value, cost_of_equity_pct)
    record = ResidualIncomeRecord(
        period=period, net_income=net_income, equity_book_value=equity_book_value,
        cost_of_equity_pct=cost_of_equity_pct,
        cost_of_equity_charge=result["cost_of_equity_charge"],
        residual_income=result["residual_income"],
        value_created=result["value_created"], notes=notes,
    )
    db.add(record)
    await db.flush()
    return record


async def save_economic_profit(db: AsyncSession, period: str, invested_capital: float,
                               roic_pct: float, wacc_pct: float,
                               notes: str | None = None) -> EconomicProfitRecord:
    result = calc_economic_profit(invested_capital, roic_pct, wacc_pct)
    record = EconomicProfitRecord(
        period=period, invested_capital=invested_capital, roic_pct=roic_pct,
        wacc_pct=wacc_pct, spread_pct=result["spread_pct"],
        economic_profit=result["economic_profit"],
        value_created=result["value_created"], notes=notes,
    )
    db.add(record)
    await db.flush()
    return record


async def save_mva(db: AsyncSession, period: str, market_value: float,
                   invested_capital: float, notes: str | None = None) -> MVARecord:
    result = calc_mva(market_value, invested_capital)
    record = MVARecord(
        period=period, market_value=market_value,
        invested_capital=invested_capital, mva=result["mva"],
        value_created=result["value_created"], notes=notes,
    )
    db.add(record)
    await db.flush()
    return record


async def save_tsr(db: AsyncSession, period: str, beginning_price: float,
                   ending_price: float, dividends_paid: float,
                   holding_period_years: int,
                   notes: str | None = None) -> TSRRecord:
    result = calc_tsr(beginning_price, ending_price, dividends_paid, holding_period_years)
    record = TSRRecord(
        period=period, beginning_price=beginning_price, ending_price=ending_price,
        dividends_paid=dividends_paid, holding_period_years=holding_period_years,
        capital_gain=result["capital_gain"],
        capital_gain_yield_pct=result["capital_gain_yield_pct"],
        dividend_yield_pct=result["dividend_yield_pct"],
        total_return_pct=result["total_return_pct"],
        annualized_tsr_pct=result["annualized_tsr_pct"], notes=notes,
    )
    db.add(record)
    await db.flush()
    return record


async def save_fcf(db: AsyncSession, period: str, operating_cash_flow: float,
                   capex: float, interest_expense: float, tax_rate_pct: float,
                   notes: str | None = None) -> FCFRecord:
    result = calc_fcf(operating_cash_flow, capex, interest_expense, tax_rate_pct)
    record = FCFRecord(
        period=period, operating_cash_flow=operating_cash_flow, capex=capex,
        interest_expense=interest_expense, tax_rate_pct=tax_rate_pct,
        after_tax_interest=result["after_tax_interest"],
        free_cash_flow=result["free_cash_flow"], notes=notes,
    )
    db.add(record)
    await db.flush()
    return record


# ── History Queries ──────────────────────────────────────────────────

MODEL_MAP = {
    "eva": EVARecord,
    "ebitda": EBITDARecord,
    "dcf": DCFValuation,
    "residual_income": ResidualIncomeRecord,
    "economic_profit": EconomicProfitRecord,
    "mva": MVARecord,
    "tsr": TSRRecord,
    "fcf": FCFRecord,
}


async def get_history(
    db: AsyncSession, record_type: str, limit: int = 50, offset: int = 0
) -> list[Any]:
    model = MODEL_MAP.get(record_type)
    if not model:
        return []
    result = await db.execute(
        select(model)
        .where(model.is_active.is_(True))
        .order_by(desc(model.created_at))
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_record_by_id(db: AsyncSession, record_type: str, record_id: int) -> Any | None:
    model = MODEL_MAP.get(record_type)
    if not model:
        return None
    result = await db.execute(select(model).where(model.id == record_id))
    return result.scalar_one_or_none()
