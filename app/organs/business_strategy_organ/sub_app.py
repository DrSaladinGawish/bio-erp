"""
Business Strategy Sub-Application for BIO-ERP v5
==================================================
Mount at: app.mount("/api/v1/business-strategy", business_strategy_app) in BIO-ERP's main.py

Techniques: Porter's Five Forces, Competitive Advantage, Differentiation Strategy,
            Cost Leadership, Focus Strategy, Value Discipline, Business Model Canvas,
            Competitive Positioning, Market Positioning, Strategic Group Mapping,
            Competitor Analysis, Industry Structure, Strategic Window
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

business_strategy_app = FastAPI(
    title="Business Strategy Microservice",
    description="Business Strategy Tools — Porter's Five Forces, Competitive Advantage, Business Model Canvas, and more",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — Porter's Five Forces
# =============================================================================


class PorterForceSchema(BaseModel):
    force_name: str = Field(..., min_length=1)
    intensity: float = Field(default=5.0, ge=1, le=10)
    description: str = Field(default="")
    key_factors: List[str] = Field(default_factory=list)


class PorterFiveForcesSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    industry: str = Field(default="")
    forces: List[PorterForceSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Business Model Canvas
# =============================================================================


class BusinessModelCanvasSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    key_partners: List[str] = Field(default_factory=list)
    key_activities: List[str] = Field(default_factory=list)
    key_resources: List[str] = Field(default_factory=list)
    value_propositions: List[str] = Field(default_factory=list)
    customer_segments: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)
    customer_relationships: List[str] = Field(default_factory=list)
    revenue_streams: List[str] = Field(default_factory=list)
    cost_structures: List[str] = Field(default_factory=list)

# =============================================================================
# PYDANTIC SCHEMAS — Value Discipline
# =============================================================================


class ValueDisciplineSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    operational_excellence: float = Field(default=5.0, ge=1, le=10)
    product_leadership: float = Field(default=5.0, ge=1, le=10)
    customer_intimacy: float = Field(default=5.0, ge=1, le=10)

# =============================================================================
# PYDANTIC SCHEMAS — Competitive Positioning
# =============================================================================


class CompetitivePositionSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    target_segment: str = Field(default="")
    price_position: float = Field(default=5.0, ge=1, le=10, description="1=Low Price, 10=Premium")
    quality_position: float = Field(default=5.0, ge=1, le=10)
    innovation_position: float = Field(default=5.0, ge=1, le=10)
    service_position: float = Field(default=5.0, ge=1, le=10)

# =============================================================================
# PYDANTIC SCHEMAS — Strategic Group Mapping
# =============================================================================


class StrategicGroupMemberSchema(BaseModel):
    member_name: str = Field(..., min_length=1)
    x_axis_value: float = Field(default=5.0, description="Primary differentiator value")
    y_axis_value: float = Field(default=5.0, description="Secondary differentiator value")
    market_share_pct: float = Field(default=0.0, ge=0, le=100)


class StrategicGroupMapSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    x_axis_label: str = Field(default="Breadth of Product Line")
    y_axis_label: str = Field(default="Quality/Price")
    members: List[StrategicGroupMemberSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Competitor Analysis
# =============================================================================


class CompetitorDetailSchema(BaseModel):
    name: str = Field(..., min_length=1)
    market_share_pct: float = Field(default=0.0, ge=0, le=100)
    revenue: float = Field(default=0.0, ge=0)
    strategy_type: str = Field(default="UNKNOWN")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    reaction_pattern: str = Field(default="UNKNOWN")


class CompetitorAnalysisSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    industry: str = Field(default="")
    competitors: List[CompetitorDetailSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Strategic Window
# =============================================================================


class StrategicWindowSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    window_name: str = Field(..., min_length=1)
    window_open: bool = Field(default=True)
    estimated_duration_months: int = Field(default=12, ge=1, le=60)
    fit_score: float = Field(default=5.0, ge=1, le=10, description="Organization's fit with the window")
    competitive_intensity: float = Field(default=5.0, ge=1, le=10)
    required_investment: float = Field(default=0.0, ge=0)

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@business_strategy_app.get("/")
def root():
    return {
        "service": "Business Strategy Microservice",
        "version": "1.0.0",
        "techniques": [
            "Porters_Five_Forces", "Competitive_Advantage", "Differentiation_Strategy",
            "Cost_Leadership", "Focus_Strategy", "Value_Discipline",
            "Business_Model_Canvas", "Competitive_Positioning", "Market_Positioning",
            "Strategic_Group_Mapping", "Competitor_Analysis", "Industry_Structure",
            "Strategic_Window",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@business_strategy_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "business-strategy",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "porters_five_forces", "competitive_advantage", "differentiation",
            "cost_leadership", "focus_strategy", "value_discipline",
            "business_model_canvas", "competitive_positioning", "market_positioning",
            "strategic_group_mapping", "competitor_analysis", "industry_structure",
            "strategic_window",
        ],
    }

# =============================================================================
# ENDPOINTS — Porter's Five Forces
# =============================================================================


@business_strategy_app.post("/five-forces/analyze")
def five_forces_analyze(data: PorterFiveForcesSchema):
    try:
        total_intensity = sum(f.intensity for f in data.forces)
        avg_intensity = total_intensity / len(data.forces) if data.forces else 0
        industry_attractiveness = "HIGH" if avg_intensity <= 4 else "MEDIUM" if avg_intensity <= 6.5 else "LOW"
        strongest = max(data.forces, key=lambda f: f.intensity) if data.forces else None
        weakest = min(data.forces, key=lambda f: f.intensity) if data.forces else None
        return {
            "success": True,
            "organization": data.organization_name,
            "industry": data.industry,
            "forces_count": len(data.forces),
            "average_intensity": round(avg_intensity, 2),
            "industry_attractiveness": industry_attractiveness,
            "strongest_force": strongest.force_name if strongest else None,
            "weakest_force": weakest.force_name if weakest else None,
            "forces": [{"name": f.force_name, "intensity": f.intensity} for f in data.forces],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Business Model Canvas
# =============================================================================


@business_strategy_app.post("/canvas/evaluate")
def canvas_evaluate(canvas: BusinessModelCanvasSchema):
    try:
        blocks = {
            "key_partners": canvas.key_partners,
            "key_activities": canvas.key_activities,
            "key_resources": canvas.key_resources,
            "value_propositions": canvas.value_propositions,
            "customer_segments": canvas.customer_segments,
            "channels": canvas.channels,
            "customer_relationships": canvas.customer_relationships,
            "revenue_streams": canvas.revenue_streams,
            "cost_structures": canvas.cost_structures,
        }
        filled = sum(1 for items in blocks.values() if items)
        completeness = filled / len(blocks) * 100
        return {
            "success": True,
            "organization": canvas.organization_name,
            "completeness_pct": round(completeness, 1),
            "blocks_filled": filled,
            "blocks_total": len(blocks),
            "block_counts": {k: len(v) for k, v in blocks.items()},
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Value Discipline
# =============================================================================


@business_strategy_app.post("/value-discipline/analyze")
def value_discipline_analyze(data: ValueDisciplineSchema):
    try:
        scores = {
            "OPERATIONAL_EXCELLENCE": data.operational_excellence,
            "PRODUCT_LEADERSHIP": data.product_leadership,
            "CUSTOMER_INTIMACY": data.customer_intimacy,
        }
        primary = max(scores, key=scores.get)
        balance = max(scores.values()) - min(scores.values())
        focus = "FOCUSED" if balance <= 2 else "WELL_BALANCED" if balance <= 4 else "DILUTED"
        return {
            "success": True,
            "organization": data.organization_name,
            "scores": {k: round(v, 2) for k, v in scores.items()},
            "primary_discipline": primary,
            "balance_score": round(balance, 2),
            "focus_level": focus,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Competitive Positioning
# =============================================================================


@business_strategy_app.post("/positioning/analyze")
def competitive_positioning_analyze(data: CompetitivePositionSchema):
    try:
        overall = (data.price_position + data.quality_position + data.innovation_position + data.service_position) / 4
        position_type = "PREMIUM" if data.price_position >= 7 else "VALUE" if data.price_position <= 3 else "MID_MARKET"
        return {
            "success": True,
            "organization": data.organization_name,
            "target_segment": data.target_segment,
            "overall_positioning": round(overall, 2),
            "position_type": position_type,
            "dimensions": {
                "price": data.price_position,
                "quality": data.quality_position,
                "innovation": data.innovation_position,
                "service": data.service_position,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategic Group Mapping
# =============================================================================


@business_strategy_app.post("/strategic-group/map")
def strategic_group_map(data: StrategicGroupMapSchema):
    try:
        groups = {}
        for m in data.members:
            quadrant_x = "HIGH" if m.x_axis_value >= 5 else "LOW"
            quadrant_y = "HIGH" if m.y_axis_value >= 5 else "LOW"
            group_key = f"{quadrant_x}_{quadrant_y}"
            groups.setdefault(group_key, []).append({
                "member": m.member_name,
                "market_share": m.market_share_pct,
            })
        return {
            "success": True,
            "organization": data.organization_name,
            "x_axis": data.x_axis_label,
            "y_axis": data.y_axis_label,
            "groups": groups,
            "total_members": len(data.members),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Competitor Analysis
# =============================================================================


@business_strategy_app.post("/competitor/analyze")
def competitor_analyze(analysis: CompetitorAnalysisSchema):
    try:
        total_share = sum(c.market_share_pct for c in analysis.competitors)
        total_revenue = sum(c.revenue for c in analysis.competitors)
        leader = max(analysis.competitors, key=lambda c: c.market_share_pct) if analysis.competitors else None
        high_threat = [c.name for c in analysis.competitors if len(c.strengths) > len(c.weaknesses)]
        return {
            "success": True,
            "organization": analysis.organization_name,
            "industry": analysis.industry,
            "competitors_count": len(analysis.competitors),
            "total_competitor_revenue": total_revenue,
            "market_leader": leader.name if leader else None,
            "market_leader_share": leader.market_share_pct if leader else 0,
            "high_threat_competitors": high_threat,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategic Window
# =============================================================================


@business_strategy_app.post("/strategic-window/evaluate")
def strategic_window_evaluate(window: StrategicWindowSchema):
    try:
        attractiveness = window.fit_score * (10 - window.competitive_intensity) / 10
        recommendation = "CAPTURE" if window.window_open and attractiveness >= 5 else "MONITOR" if window.window_open else "SKIP"
        return {
            "success": True,
            "organization": window.organization_name,
            "window_name": window.window_name,
            "is_open": window.window_open,
            "estimated_duration_months": window.estimated_duration_months,
            "attractiveness_score": round(attractiveness, 2),
            "recommendation": recommendation,
            "required_investment": window.required_investment,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/business-strategy"):
    parent_app.mount(prefix, business_strategy_app)
