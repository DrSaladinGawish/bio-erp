"""
Financial & Value-Based Strategy Organ for BIO-ERP v5
======================================================
Mount at: app.mount("/api/v1/financial-value", financial_value_app)

8 techniques: EVA, EBITDA, DCF, Residual Income, Economic Profit, MVA, TSR, FCF
Each endpoint persists results to DB and optionally overlays ANN predictions.
"""

from fastapi import FastAPI, HTTPException, Depends
from typing import Any

from app.database import get_db
from app.services import financial_value as svc
from app.schemas.financial_value import (
    EVARequest,
    EBITDARequest,
    DCFRequest,
    ResidualIncomeRequest,
    EconomicProfitRequest,
    MVARequest,
    TSRRequest,
    FCFRequest,
)

financial_value_app = FastAPI(
    title="Financial & Value-Based Strategy Organ",
    description="8 techniques — EVA, EBITDA, DCF, Residual Income, Economic Profit, MVA, TSR, FCF",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


@financial_value_app.get("/")
def root():
    return {
        "service": "Financial & Value-Based Strategy Organ",
        "version": "2.0.0",
        "techniques_count": 8,
        "techniques": [
            "Economic Value Added (EVA)",
            "EBITDA Analysis",
            "Discounted Cash Flow (DCF)",
            "Residual Income",
            "Economic Profit",
            "Market Value Added (MVA)",
            "Total Shareholder Return (TSR)",
            "Free Cash Flow (FCF)",
        ],
        "docs": "/docs",
    }


@financial_value_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "organ": "financial-value",
        "version": "2.0.0",
        "techniques_ready": 8,
    }


# ── EVA ──────────────────────────────────────────────────────────────


@financial_value_app.post("/eva/calculate")
async def eva_calculate(req: EVARequest, db=Depends(get_db)):
    try:
        record = await svc.save_eva(
            db, req.period, req.nopat, req.capital_employed,
            req.wacc_pct, req.notes,
        )
        await db.commit()
        result = svc.calc_eva(req.nopat, req.capital_employed, req.wacc_pct)
        return {
            "success": True,
            "record_id": record.id,
            "period": req.period,
            **result,
            "ann_predicted_eva": record.ann_predicted_eva,
            "ann_confidence": record.ann_confidence,
            "model_version": "2.0-ann" if record.ann_predicted_eva else "1.0-heuristic",
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ── EBITDA ───────────────────────────────────────────────────────────


@financial_value_app.post("/ebitda/analyze")
async def ebitda_analyze(req: EBITDARequest, db=Depends(get_db)):
    try:
        record = await svc.save_ebitda(
            db, req.period, req.revenue, req.cogs, req.opex, req.da, req.notes,
        )
        await db.commit()
        result = svc.calc_ebitda(req.revenue, req.cogs, req.opex, req.da)
        return {
            "success": True,
            "record_id": record.id,
            "period": req.period,
            **result,
            "ann_predicted_ebitda": record.ann_predicted_ebitda,
            "ann_confidence": record.ann_confidence,
            "model_version": "2.0-ann" if record.ann_predicted_ebitda else "1.0-heuristic",
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ── DCF ──────────────────────────────────────────────────────────────


@financial_value_app.post("/dcf/valuation")
async def dcf_valuation(req: DCFRequest, db=Depends(get_db)):
    try:
        record = await svc.save_dcf(
            db, req.company_name, req.cash_flows,
            req.discount_rate_pct, req.terminal_growth_pct, req.notes,
        )
        await db.commit()
        result = svc.calc_dcf(req.cash_flows, req.discount_rate_pct, req.terminal_growth_pct)
        return {
            "success": True,
            "record_id": record.id,
            "company_name": req.company_name,
            **result,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ── Residual Income ──────────────────────────────────────────────────


@financial_value_app.post("/residual-income/calculate")
async def residual_income_calculate(req: ResidualIncomeRequest, db=Depends(get_db)):
    try:
        record = await svc.save_residual_income(
            db, req.period, req.net_income, req.equity_book_value,
            req.cost_of_equity_pct, req.notes,
        )
        await db.commit()
        result = svc.calc_residual_income(req.net_income, req.equity_book_value, req.cost_of_equity_pct)
        return {
            "success": True,
            "record_id": record.id,
            "period": req.period,
            **result,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ── Economic Profit ──────────────────────────────────────────────────


@financial_value_app.post("/economic-profit/calculate")
async def economic_profit_calculate(req: EconomicProfitRequest, db=Depends(get_db)):
    try:
        record = await svc.save_economic_profit(
            db, req.period, req.invested_capital, req.roic_pct,
            req.wacc_pct, req.notes,
        )
        await db.commit()
        result = svc.calc_economic_profit(req.invested_capital, req.roic_pct, req.wacc_pct)
        return {
            "success": True,
            "record_id": record.id,
            "period": req.period,
            **result,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ── MVA ──────────────────────────────────────────────────────────────


@financial_value_app.post("/mva/calculate")
async def mva_calculate(req: MVARequest, db=Depends(get_db)):
    try:
        record = await svc.save_mva(
            db, req.period, req.market_value, req.invested_capital, req.notes,
        )
        await db.commit()
        result = svc.calc_mva(req.market_value, req.invested_capital)
        return {
            "success": True,
            "record_id": record.id,
            "period": req.period,
            **result,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ── TSR ──────────────────────────────────────────────────────────────


@financial_value_app.post("/tsr/calculate")
async def tsr_calculate(req: TSRRequest, db=Depends(get_db)):
    try:
        record = await svc.save_tsr(
            db, req.period, req.beginning_price, req.ending_price,
            req.dividends_paid, req.holding_period_years, req.notes,
        )
        await db.commit()
        result = svc.calc_tsr(
            req.beginning_price, req.ending_price,
            req.dividends_paid, req.holding_period_years,
        )
        return {
            "success": True,
            "record_id": record.id,
            "period": req.period,
            **result,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ── FCF ──────────────────────────────────────────────────────────────


@financial_value_app.post("/fcf/calculate")
async def fcf_calculate(req: FCFRequest, db=Depends(get_db)):
    try:
        record = await svc.save_fcf(
            db, req.period, req.operating_cash_flow, req.capex,
            req.interest_expense, req.tax_rate_pct, req.notes,
        )
        await db.commit()
        result = svc.calc_fcf(
            req.operating_cash_flow, req.capex,
            req.interest_expense, req.tax_rate_pct,
        )
        return {
            "success": True,
            "record_id": record.id,
            "period": req.period,
            **result,
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


# ── History Endpoints ────────────────────────────────────────────────


@financial_value_app.get("/history/{record_type}")
async def get_history(record_type: str, limit: int = 50, offset: int = 0, db=Depends(get_db)):
    records = await svc.get_history(db, record_type, limit, offset)
    return {
        "success": True,
        "record_type": record_type,
        "total": len(records),
        "records": [
            {"id": r.id, "period": getattr(r, "period", getattr(r, "company_name", "")),
             "created_at": r.created_at.isoformat() if r.created_at else None,
             "is_active": r.is_active}
            for r in records
        ],
    }
