"""
Corporate Strategy Sub-Application for BIO-ERP v5
===================================================
Mount at: app.mount("/api/v1/corporate-strategy", corporate_strategy_app) in BIO-ERP's main.py

Techniques: Diversification Strategy, Mergers & Acquisitions, Strategic Alliances,
            Corporate Restructuring, Portfolio Restructuring
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

corporate_strategy_app = FastAPI(
    title="Corporate Strategy Microservice",
    description="Corporate Strategy Analysis — Diversification, M&A, Strategic Alliances, Restructuring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — Diversification Strategy
# =============================================================================


class DiversificationInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    diversification_type: str = Field(..., description="RELATED_CONCENTRIC, RELATED_HORIZONTAL, UNRELATED")
    synergy_potential: float = Field(default=5.0, ge=1, le=10)
    resource_overlap_pct: float = Field(default=0.0, ge=0, le=100)
    risk_level: str = Field(default="MEDIUM")
    investment: float = Field(default=0.0, ge=0)
    expected_return_pct: float = Field(default=0.0)
    timeline_months: int = Field(default=12, ge=1, le=120)


class DiversificationStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    current_core_businesses: List[str] = Field(default_factory=list)
    initiatives: List[DiversificationInitiativeSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Mergers & Acquisitions
# =============================================================================


class MASchema(BaseModel):
    deal_name: str = Field(..., min_length=1)
    target_name: str = Field(..., min_length=1)
    deal_type: str = Field(..., description="MERGER, ACQUISITION, REVERSE_MERGER, ASSET_PURCHASE")
    deal_value: float = Field(..., gt=0)
    expected_synergies: float = Field(default=0.0, ge=0)
    integration_risk: str = Field(default="MEDIUM")
    strategic_rationale: str = Field(default="")
    cultural_fit: float = Field(default=5.0, ge=1, le=10)
    due_diligence_status: str = Field(default="PENDING")

# =============================================================================
# PYDANTIC SCHEMAS — Strategic Alliances
# =============================================================================


class AllianceSchema(BaseModel):
    alliance_name: str = Field(..., min_length=1)
    partner_name: str = Field(..., min_length=1)
    alliance_type: str = Field(..., description="EQUITY, NON_EQUITY, JOINT_VENTURE, CONSORTIUM")
    objective: str = Field(default="")
    resource_contribution: str = Field(default="")
    governance_model: str = Field(default="JOINT_COMMITTEE")
    expected_duration_years: int = Field(default=3, ge=1, le=20)
    synergy_score: float = Field(default=5.0, ge=1, le=10)

# =============================================================================
# PYDANTIC SCHEMAS — Corporate Restructuring
# =============================================================================


class RestructuringInitiativeSchema(BaseModel):
    initiative_name: str = Field(..., min_length=1)
    restructuring_type: str = Field(..., description="DOWNSIZING, SPIN_OFF, SPLIT_OFF, EQUITY_CARVE_OUT, LIQUIDATION")
    affected_units: List[str] = Field(default_factory=list)
    expected_savings: float = Field(default=0.0, ge=0)
    restructuring_cost: float = Field(default=0.0, ge=0)
    timeline_months: int = Field(default=6, ge=1, le=60)
    employee_impact: str = Field(default="LOW")

# =============================================================================
# PYDANTIC SCHEMAS — Portfolio Restructuring
# =============================================================================


class PortfolioBusinessSchema(BaseModel):
    business_name: str = Field(..., min_length=1)
    revenue: float = Field(..., ge=0)
    profit_margin_pct: float = Field(default=0.0)
    growth_rate_pct: float = Field(default=0.0)
    strategic_fit: float = Field(default=5.0, ge=1, le=10)
    market_share_pct: float = Field(default=0.0, ge=0, le=100)
    action: str = Field(default="HOLD", description="INVEST, HOLD, HARVEST, DIVEST")


class PortfolioRestructuringSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    businesses: List[PortfolioBusinessSchema]
    total_target_budget: float = Field(..., gt=0)

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@corporate_strategy_app.get("/")
def root():
    return {
        "service": "Corporate Strategy Microservice",
        "version": "1.0.0",
        "techniques": [
            "Diversification_Strategy", "Mergers_Acquisitions",
            "Strategic_Alliances", "Corporate_Restructuring",
            "Portfolio_Restructuring",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@corporate_strategy_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "corporate-strategy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "diversification", "mergers_acquisitions",
            "strategic_alliances", "corporate_restructuring",
            "portfolio_restructuring",
        ],
    }

# =============================================================================
# ENDPOINTS — Diversification Strategy
# =============================================================================


@corporate_strategy_app.post("/diversification/analyze")
def diversification_analyze(strategy: DiversificationStrategySchema):
    try:
        results = []
        total_investment = 0
        for init in strategy.initiatives:
            roi_score = init.expected_return_pct / 100 * init.synergy_potential
            recommendation = "PURSUE" if roi_score >= 5 and init.risk_level != "HIGH" else "EVALUATE" if roi_score >= 3 else "DEFER"
            total_investment += init.investment
            results.append({
                "initiative": init.initiative_name,
                "type": init.diversification_type,
                "synergy": init.synergy_potential,
                "roi_score": round(roi_score, 2),
                "recommendation": recommendation,
            })
        return {
            "success": True,
            "organization": strategy.organization_name,
            "core_businesses": strategy.current_core_businesses,
            "initiatives_count": len(strategy.initiatives),
            "total_investment": total_investment,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Mergers & Acquisitions
# =============================================================================


@corporate_strategy_app.post("/ma/evaluate")
def ma_evaluate(deals: List[MASchema]):
    try:
        results = []
        total_value = 0
        total_synergies = 0
        for deal in deals:
            net_value = deal.expected_synergies - deal.deal_value * 0.1
            risk_adjusted = net_value * (0.8 if deal.integration_risk == "LOW" else 0.5 if deal.integration_risk == "MEDIUM" else 0.3)
            cultural_factor = deal.cultural_fit / 10
            viability = "HIGH" if risk_adjusted > 0 and cultural_factor >= 0.7 else "MEDIUM" if risk_adjusted > 0 else "LOW"
            total_value += deal.deal_value
            total_synergies += deal.expected_synergies
            results.append({
                "deal": deal.deal_name,
                "target": deal.target_name,
                "type": deal.deal_type,
                "value": deal.deal_value,
                "expected_synergies": deal.expected_synergies,
                "viability": viability,
                "cultural_fit": deal.cultural_fit,
            })
        return {
            "success": True,
            "deals_count": len(deals),
            "total_deal_value": total_value,
            "total_expected_synergies": total_synergies,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategic Alliances
# =============================================================================


@corporate_strategy_app.post("/alliance/evaluate")
def alliance_evaluate(alliances: List[AllianceSchema]):
    try:
        results = []
        for a in alliances:
            strategic_value = a.synergy_score * (1.2 if a.alliance_type == "JOINT_VENTURE" else 1.0)
            governance_fit = "GOOD" if a.governance_model in ("JOINT_COMMITTEE", "MANAGEMENT_BOARD") else "ADEQUATE"
            results.append({
                "alliance": a.alliance_name,
                "partner": a.partner_name,
                "type": a.alliance_type,
                "strategic_value": round(strategic_value, 2),
                "governance_fit": governance_fit,
                "expected_duration": a.expected_duration_years,
            })
        avg_synergy = sum(a.synergy_score for a in alliances) / len(alliances) if alliances else 0
        return {
            "success": True,
            "alliances_count": len(alliances),
            "average_synergy_score": round(avg_synergy, 2),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Corporate Restructuring
# =============================================================================


@corporate_strategy_app.post("/restructuring/analyze")
def restructuring_analyze(initiatives: List[RestructuringInitiativeSchema]):
    try:
        results = []
        total_savings = 0
        total_cost = 0
        for init in initiatives:
            roi = (init.expected_savings - init.restructuring_cost) / init.restructuring_cost * 100 if init.restructuring_cost > 0 else 0
            total_savings += init.expected_savings
            total_cost += init.restructuring_cost
            results.append({
                "initiative": init.initiative_name,
                "type": init.restructuring_type,
                "expected_savings": init.expected_savings,
                "cost": init.restructuring_cost,
                "roi_pct": round(roi, 1),
                "timeline_months": init.timeline_months,
            })
        net_benefit = total_savings - total_cost
        return {
            "success": True,
            "initiatives_count": len(initiatives),
            "total_expected_savings": total_savings,
            "total_restructuring_cost": total_cost,
            "net_benefit": net_benefit,
            "overall_roi_pct": round(net_benefit / total_cost * 100, 1) if total_cost > 0 else 0,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Portfolio Restructuring
# =============================================================================


@corporate_strategy_app.post("/portfolio/analyze")
def portfolio_restructuring_analyze(data: PortfolioRestructuringSchema):
    try:
        action_summary = {}
        divest_proceeds = 0
        invest_required = 0
        for biz in data.businesses:
            action_summary.setdefault(biz.action, []).append(biz.business_name)
            if biz.action == "DIVEST":
                divest_proceeds += biz.revenue * 0.8
            elif biz.action == "INVEST":
                invest_required += biz.revenue * 0.2
        total_revenue = sum(b.revenue for b in data.businesses)
        portfolio_health = "HEALTHY" if invest_required <= data.total_target_budget else "CONSTRAINED"
        return {
            "success": True,
            "organization": data.organization_name,
            "businesses_count": len(data.businesses),
            "total_revenue": total_revenue,
            "action_distribution": {k: len(v) for k, v in action_summary.items()},
            "estimated_divest_proceeds": round(divest_proceeds, 2),
            "estimated_investment_required": round(invest_required, 2),
            "budget_status": portfolio_health,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/corporate-strategy"):
    parent_app.mount(prefix, corporate_strategy_app)
