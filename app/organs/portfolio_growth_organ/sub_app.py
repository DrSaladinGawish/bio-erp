"""
Portfolio & Growth Strategies Sub-Application for BIO-ERP v5
============================================================
Mount at: app.mount("/api/v1/portfolio-growth", portfolio_growth_app) in BIO-ERP's main.py

Techniques: BCG Growth-Share Matrix, GE/McKinsey Matrix, Ansoff Growth Matrix, ADL Matrix,
            Directional Policy Matrix, Product Lifecycle, Portfolio Management,
            Diversification Analysis, Market Entry/Exit
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

portfolio_growth_app = FastAPI(
    title="Portfolio & Growth Strategies Microservice",
    description="Portfolio & Growth Strategy Analysis — BCG, GE/McKinsey, Ansoff, ADL, DPM, Product Lifecycle, and more",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — BCG Growth-Share Matrix
# =============================================================================


class BCGProductSchema(BaseModel):
    product_name: str = Field(..., min_length=1)
    market_share_pct: float = Field(..., ge=0, le=100)
    market_growth_rate_pct: float = Field(...)
    revenue: float = Field(default=0.0, ge=0)
    investment: float = Field(default=0.0, ge=0)


class BCGGrowthShareSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    products: List[BCGProductSchema]

# =============================================================================
# PYDANTIC SCHEMAS — GE/McKinsey Matrix
# =============================================================================


class GEBusinessUnitSchema(BaseModel):
    unit_name: str = Field(..., min_length=1)
    industry_attractiveness: float = Field(..., ge=1, le=10)
    competitive_strength: float = Field(..., ge=1, le=10)
    market_size: float = Field(default=0.0, ge=0)
    growth_rate_pct: float = Field(default=0.0)
    revenue: float = Field(default=0.0, ge=0)


class GEMcKinseySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    business_units: List[GEBusinessUnitSchema]

# =============================================================================
# PYDANTIC SCHEMAS — ADL Matrix
# =============================================================================


class ADLProductSchema(BaseModel):
    product_name: str = Field(..., min_length=1)
    industry_maturity: str = Field(..., description="EMERGENT, GROWTH, MATURE, AGING")
    competitive_position: str = Field(..., description="DOMINANT, STRONG, FAVORABLE, TENABLE, WEAK")
    market_share_pct: float = Field(default=0.0, ge=0, le=100)


class ADLMatrixSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    products: List[ADLProductSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Directional Policy Matrix
# =============================================================================


class DPMBusinessSchema(BaseModel):
    unit_name: str = Field(..., min_length=1)
    business_prospects: float = Field(..., ge=1, le=10)
    competitive_position: float = Field(..., ge=1, le=10)
    market_share_pct: float = Field(default=0.0, ge=0, le=100)
    revenue: float = Field(default=0.0, ge=0)


class DPMMatrixSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    business_units: List[DPMBusinessSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Product Lifecycle
# =============================================================================


class ProductLifecycleSchema(BaseModel):
    product_name: str = Field(..., min_length=1)
    current_stage: str = Field(..., description="INTRODUCTION, GROWTH, MATURITY, DECLINE")
    launch_year: int = Field(default=2020)
    revenue: float = Field(default=0.0, ge=0)
    growth_rate_pct: float = Field(default=0.0)
    profit_margin_pct: float = Field(default=0.0)
    market_share_pct: float = Field(default=0.0, ge=0, le=100)


class PortfolioLifecycleSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    products: List[ProductLifecycleSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Portfolio Management
# =============================================================================


class PortfolioItemSchema(BaseModel):
    unit_name: str = Field(..., min_length=1)
    revenue: float = Field(..., ge=0)
    profit_margin_pct: float = Field(default=0.0)
    growth_rate_pct: float = Field(default=0.0)
    risk_level: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH")
    strategic_fit: float = Field(default=5.0, ge=1, le=10)


class PortfolioManagementSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    items: List[PortfolioItemSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Diversification Analysis
# =============================================================================


class DiversificationOptionSchema(BaseModel):
    option_name: str = Field(..., min_length=1)
    type: str = Field(..., description="RELATED_CONCENTRIC, RELATED_HORIZONTAL, UNRELATED_CONGLOMERATE")
    synergy_score: float = Field(default=5.0, ge=1, le=10)
    risk: str = Field(default="MEDIUM")
    investment: float = Field(default=0.0, ge=0)
    expected_return_pct: float = Field(default=0.0)


class DiversificationAnalysisSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    current_businesses: List[str] = Field(default_factory=list)
    options: List[DiversificationOptionSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Market Entry/Exit
# =============================================================================


class MarketEntryExitSchema(BaseModel):
    market_name: str = Field(..., min_length=1)
    action: str = Field(..., description="ENTRY, EXPANSION, WITHDRAWAL, HARVEST")
    market_size: float = Field(default=0.0, ge=0)
    entry_barrier: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH")
    competitive_intensity: float = Field(default=5.0, ge=1, le=10)
    investment_required: float = Field(default=0.0, ge=0)
    expected_roi_pct: float = Field(default=0.0)
    timeframe_years: int = Field(default=3, ge=1, le=20)

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@portfolio_growth_app.get("/")
def root():
    return {
        "service": "Portfolio & Growth Strategies Microservice",
        "version": "1.0.0",
        "techniques": [
            "BCG_Growth_Share", "GE_McKinsey", "Ansoff_Growth",
            "ADL_Matrix", "Directional_Policy_Matrix", "Product_Lifecycle",
            "Portfolio_Management", "Diversification_Analysis", "Market_Entry_Exit",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@portfolio_growth_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "portfolio-growth",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "bcg_growth_share", "ge_mckinsey", "ansoff_growth",
            "adl_matrix", "dpm", "product_lifecycle",
            "portfolio_management", "diversification", "market_entry_exit",
        ],
    }

# =============================================================================
# ENDPOINTS — BCG Growth-Share Matrix
# =============================================================================


@portfolio_growth_app.post("/bcg/analyze")
def bcg_analyze(matrix: BCGGrowthShareSchema):
    try:
        categories = {"STAR": [], "CASH_COW": [], "QUESTION_MARK": [], "DOG": []}
        for p in matrix.products:
            high_share = p.market_share_pct >= 50
            high_growth = p.market_growth_rate_pct > 0
            if high_share and high_growth:
                categories["STAR"].append(p.product_name)
            elif high_share and not high_growth:
                categories["CASH_COW"].append(p.product_name)
            elif not high_share and high_growth:
                categories["QUESTION_MARK"].append(p.product_name)
            else:
                categories["DOG"].append(p.product_name)
        total_revenue = sum(p.revenue for p in matrix.products)
        total_investment = sum(p.investment for p in matrix.products)
        return {
            "success": True,
            "organization": matrix.organization_name,
            "categories": {k: {"count": len(v), "products": v} for k, v in categories.items()},
            "total_products": len(matrix.products),
            "total_revenue": total_revenue,
            "total_investment": total_investment,
            "cash_flow_balance": "POSITIVE" if len(categories["CASH_COW"]) >= len(categories["STAR"]) else "NEGATIVE",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — GE/McKinsey Matrix
# =============================================================================


@portfolio_growth_app.post("/ge-mckinsey/analyze")
def ge_mckinsey_analyze(matrix: GEMcKinseySchema):
    try:
        invest = []
        hold = []
        harvest_divest = []
        for bu in matrix.business_units:
            composite = (bu.industry_attractiveness + bu.competitive_strength) / 2
            if composite >= 7:
                action = "INVEST"
                invest.append(bu.unit_name)
            elif composite >= 4:
                action = "HOLD"
                hold.append(bu.unit_name)
            else:
                action = "HARVEST/DIVEST"
                harvest_divest.append(bu.unit_name)
        total_revenue = sum(bu.revenue for bu in matrix.business_units)
        return {
            "success": True,
            "organization": matrix.organization_name,
            "invest": invest,
            "hold": hold,
            "harvest_divest": harvest_divest,
            "total_units": len(matrix.business_units),
            "total_revenue": total_revenue,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — ADL Matrix
# =============================================================================


@portfolio_growth_app.post("/adl/analyze")
def adl_analyze(matrix: ADLMatrixSchema):
    try:
        maturity_order = {"EMERGENT": 1, "GROWTH": 2, "MATURE": 3, "AGING": 4}
        position_order = {"DOMINANT": 5, "STRONG": 4, "FAVORABLE": 3, "TENABLE": 2, "WEAK": 1}
        results = []
        for p in matrix.products:
            mat = maturity_order.get(p.industry_maturity, 2)
            pos = position_order.get(p.competitive_position, 2)
            if mat <= 2 and pos >= 4:
                strategy = "INVEST_GROW"
            elif mat >= 3 and pos >= 4:
                strategy = "PROFIT_HARVEST"
            elif mat <= 2 and pos <= 2:
                strategy = "SELECTIVE"
            else:
                strategy = "DIVEST_WITHDRAW"
            results.append({
                "product": p.product_name,
                "maturity": p.industry_maturity,
                "position": p.competitive_position,
                "recommended_strategy": strategy,
            })
        return {
            "success": True,
            "organization": matrix.organization_name,
            "products": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Directional Policy Matrix
# =============================================================================


@portfolio_growth_app.post("/dpm/analyze")
def dpm_analyze(matrix: DPMMatrixSchema):
    try:
        results = []
        for bu in matrix.business_units:
            composite = (bu.business_prospects + bu.competitive_position) / 2
            if composite >= 7:
                category = "LEADERSHIP"
            elif composite >= 5:
                category = "GROWTH"
            elif composite >= 3:
                category = "PHASED_WITHDRAWAL"
            else:
                category = "DOUBLE_OR_QUIT"
            results.append({
                "unit": bu.unit_name,
                "business_prospects": bu.business_prospects,
                "competitive_position": bu.competitive_position,
                "category": category,
            })
        return {
            "success": True,
            "organization": matrix.organization_name,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Product Lifecycle
# =============================================================================


@portfolio_growth_app.post("/lifecycle/analyze")
def lifecycle_analyze(portfolio: PortfolioLifecycleSchema):
    try:
        stage_summary = {}
        total_revenue = 0
        total_growth = 0
        for p in portfolio.products:
            stage_summary.setdefault(p.current_stage, []).append(p.product_name)
            total_revenue += p.revenue
            total_growth += p.growth_rate_pct
        avg_growth = total_growth / len(portfolio.products) if portfolio.products else 0
        health = "HEALTHY" if "GROWTH" in stage_summary or "MATURITY" in stage_summary else "AT_RISK"
        return {
            "success": True,
            "organization": portfolio.organization_name,
            "stage_distribution": {k: len(v) for k, v in stage_summary.items()},
            "total_products": len(portfolio.products),
            "total_revenue": total_revenue,
            "average_growth_rate": round(avg_growth, 2),
            "portfolio_health": health,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Portfolio Management
# =============================================================================


@portfolio_growth_app.post("/management/analyze")
def portfolio_management_analyze(portfolio: PortfolioManagementSchema):
    try:
        total_revenue = sum(item.revenue for item in portfolio.items)
        total_profit = sum(item.revenue * item.profit_margin_pct / 100 for item in portfolio.items)
        avg_growth = sum(item.growth_rate_pct for item in portfolio.items) / len(portfolio.items) if portfolio.items else 0
        avg_fit = sum(item.strategic_fit for item in portfolio.items) / len(portfolio.items) if portfolio.items else 0
        high_risk = [item.unit_name for item in portfolio.items if item.risk_level == "HIGH"]
        return {
            "success": True,
            "organization": portfolio.organization_name,
            "total_units": len(portfolio.items),
            "total_revenue": total_revenue,
            "total_profit": round(total_profit, 2),
            "average_growth_rate": round(avg_growth, 2),
            "average_strategic_fit": round(avg_fit, 2),
            "high_risk_units": high_risk,
            "concentration_risk": "HIGH" if len(portfolio.items) <= 2 else "MEDIUM" if len(portfolio.items) <= 5 else "LOW",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Diversification Analysis
# =============================================================================


@portfolio_growth_app.post("/diversification/analyze")
def diversification_analyze(analysis: DiversificationAnalysisSchema):
    try:
        results = []
        for opt in analysis.options:
            if opt.type == "RELATED_CONCENTRIC" and opt.synergy_score >= 7:
                recommendation = "STRONG_RECOMMEND"
            elif opt.type == "RELATED_HORIZONTAL":
                recommendation = "RECOMMEND" if opt.synergy_score >= 5 else "CONSIDER"
            else:
                recommendation = "PROCEED_WITH_CAUTION" if opt.risk != "HIGH" else "AVOID"
            results.append({
                "option": opt.option_name,
                "type": opt.type,
                "synergy": opt.synergy_score,
                "recommendation": recommendation,
            })
        return {
            "success": True,
            "organization": analysis.organization_name,
            "current_businesses": analysis.current_businesses,
            "options_count": len(analysis.options),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Market Entry/Exit
# =============================================================================


@portfolio_growth_app.post("/market-entry/analyze")
def market_entry_exit_analyze(markets: List[MarketEntryExitSchema]):
    try:
        results = []
        for m in markets:
            attractiveness = (10 - m.competitive_intensity) + (10 if m.entry_barrier == "LOW" else 5 if m.entry_barrier == "HIGH" else 7)
            if m.action in ("ENTRY", "EXPANSION"):
                recommendation = "PROCEED" if attractiveness >= 10 else "CONDITIONAL" if attractiveness >= 7 else "RECONSIDER"
            else:
                recommendation = "EXECUTE" if m.action == "WITHDRAWAL" else "OPTIMIZE"
            results.append({
                "market": m.market_name,
                "action": m.action,
                "attractiveness_score": round(attractiveness, 2),
                "recommendation": recommendation,
                "expected_roi": m.expected_roi_pct,
            })
        invest = [r for r in results if r["recommendation"] in ("PROCEED", "EXECUTE")]
        return {
            "success": True,
            "markets_analyzed": len(markets),
            "results": results,
            "actionable_count": len(invest),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/portfolio-growth"):
    parent_app.mount(prefix, portfolio_growth_app)
