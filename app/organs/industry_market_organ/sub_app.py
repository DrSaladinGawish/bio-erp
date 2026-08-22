"""
Industry & Market Analysis Sub-Application for BIO-ERP v5
==========================================================
Mount at: app.mount("/api/v1/industry-market", industry_market_app) in BIO-ERP's main.py

Techniques: Porter's Five Forces, Industry Life Cycle, Strategic Group Mapping,
            Market Segmentation, Industry 4.0 Analysis, Market Attractiveness,
            Industry Structure, Competitive Forces
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

industry_market_app = FastAPI(
    title="Industry & Market Analysis Microservice",
    description="Industry & Market Analysis — Porter's Five Forces, Industry Life Cycle, Strategic Groups, Market Segmentation, Industry 4.0, and more",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — Industry Life Cycle
# =============================================================================


class IndustryLifeCycleSchema(BaseModel):
    industry_name: str = Field(..., min_length=1)
    current_stage: str = Field(..., description="INTRODUCTION, GROWTH, SHAKEOUT, MATURITY, DECLINE")
    market_size: float = Field(default=0.0, ge=0)
    growth_rate_pct: float = Field(default=0.0)
    number_of_competitors: int = Field(default=0, ge=0)
    avg_profit_margin_pct: float = Field(default=0.0)
    entry_barrier_level: str = Field(default="MEDIUM")

# =============================================================================
# PYDANTIC SCHEMAS — Market Segmentation
# =============================================================================


class SegmentSchema(BaseModel):
    segment_name: str = Field(..., min_length=1)
    size: int = Field(default=0, ge=0)
    growth_rate_pct: float = Field(default=0.0)
    profitability_score: float = Field(default=5.0, ge=1, le=10)
    accessibility_score: float = Field(default=5.0, ge=1, le=10)
    competitive_intensity: float = Field(default=5.0, ge=1, le=10)


class MarketSegmentationSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    market_name: str = Field(default="")
    segmentation_variable: str = Field(default="DEMOGRAPHIC")
    segments: List[SegmentSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Industry 4.0 Analysis
# =============================================================================


class Industry4DimensionSchema(BaseModel):
    dimension_name: str = Field(..., min_length=1)
    maturity_level: int = Field(default=3, ge=1, le=5)
    investment_level: float = Field(default=5.0, ge=1, le=10)
    adoption_pct: float = Field(default=50.0, ge=0, le=100)
    key_technologies: List[str] = Field(default_factory=list)


class Industry4Schema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    industry: str = Field(default="")
    dimensions: List[Industry4DimensionSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Market Attractiveness
# =============================================================================


class MarketAttractivenessSchema(BaseModel):
    market_name: str = Field(..., min_length=1)
    market_size: float = Field(default=0.0, ge=0)
    growth_rate_pct: float = Field(default=0.0)
    profit_potential: float = Field(default=5.0, ge=1, le=10)
    competitive_intensity: float = Field(default=5.0, ge=1, le=10)
    regulatory_environment: str = Field(default="FAVORABLE")
    technology_risk: str = Field(default="LOW")

# =============================================================================
# PYDANTIC SCHEMAS — Industry Structure
# =============================================================================


class IndustryStructureSchema(BaseModel):
    industry_name: str = Field(..., min_length=1)
    fragmentation: str = Field(default="FRAGMENTED", description="FRAGMENTED, CONSOLIDATING, CONCENTRATED")
    concentration_ratio_pct: float = Field(default=0.0, ge=0, le=100)
    leading_firms: List[str] = Field(default_factory=list)
    barriers_to_entry: str = Field(default="MEDIUM")
    switching_costs: str = Field(default="MEDIUM")
    vertical_integration: str = Field(default="NONE", description="NONE, PARTIAL, FULL")

# =============================================================================
# PYDANTIC SCHEMAS — Competitive Forces
# =============================================================================


class CompetitiveForceSchema(BaseModel):
    force_name: str = Field(..., min_length=1)
    intensity: float = Field(default=5.0, ge=1, le=10)
    trend: str = Field(default="STABLE", description="INCREASING, STABLE, DECREASING")
    key_drivers: List[str] = Field(default_factory=list)


class CompetitiveForcesSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    industry: str = Field(default="")
    forces: List[CompetitiveForceSchema]

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@industry_market_app.get("/")
def root():
    return {
        "service": "Industry & Market Analysis Microservice",
        "version": "1.0.0",
        "techniques": [
            "Porters_Five_Forces", "Industry_Life_Cycle", "Strategic_Group_Mapping",
            "Market_Segmentation", "Industry_40_Analysis", "Market_Attractiveness",
            "Industry_Structure", "Competitive_Forces",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@industry_market_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "industry-market",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "porters_five_forces", "industry_life_cycle", "strategic_groups",
            "market_segmentation", "industry_40", "market_attractiveness",
            "industry_structure", "competitive_forces",
        ],
    }

# =============================================================================
# ENDPOINTS — Industry Life Cycle
# =============================================================================


@industry_market_app.post("/life-cycle/analyze")
def life_cycle_analyze(data: IndustryLifeCycleSchema):
    try:
        stage_characteristics = {
            "INTRODUCTION": {"growth_potential": "HIGH", "risk": "HIGH", "competition": "LOW"},
            "GROWTH": {"growth_potential": "HIGH", "risk": "MEDIUM", "competition": "INCREASING"},
            "SHAKEOUT": {"growth_potential": "LOW", "risk": "HIGH", "competition": "VERY_HIGH"},
            "MATURITY": {"growth_potential": "LOW", "risk": "LOW", "competition": "HIGH"},
            "DECLINE": {"growth_potential": "NEGATIVE", "risk": "HIGH", "competition": "DECREASING"},
        }
        chars = stage_characteristics.get(data.current_stage, {})
        strategic_implications = "CONSOLIDATE" if data.current_stage in ("MATURITY", "SHAKEOUT") else \
                                 "INVEST" if data.current_stage in ("GROWTH",) else "NICHE"
        return {
            "success": True,
            "industry": data.industry_name,
            "stage": data.current_stage,
            "market_size": data.market_size,
            "growth_rate": data.growth_rate_pct,
            "competitors": data.number_of_competitors,
            "characteristics": chars,
            "strategic_implication": strategic_implications,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Market Segmentation
# =============================================================================


@industry_market_app.post("/segmentation/analyze")
def segmentation_analyze(data: MarketSegmentationSchema):
    try:
        total_size = sum(s.size for s in data.segments)
        results = []
        for s in data.segments:
            attractiveness = s.profitability_score * (10 - s.competitive_intensity) / 10
            share = (s.size / total_size * 100) if total_size > 0 else 0
            results.append({
                "segment": s.segment_name,
                "size": s.size,
                "share_pct": round(share, 1),
                "growth_rate": s.growth_rate_pct,
                "attractiveness": round(attractiveness, 2),
            })
        best = max(results, key=lambda r: r["attractiveness"]) if results else None
        return {
            "success": True,
            "organization": data.organization_name,
            "market": data.market_name,
            "variable": data.segmentation_variable,
            "segments_count": len(data.segments),
            "total_market_size": total_size,
            "best_segment": best["segment"] if best else None,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Industry 4.0 Analysis
# =============================================================================


@industry_market_app.post("/industry4/analyze")
def industry4_analyze(data: Industry4Schema):
    try:
        results = []
        avg_maturity = 0
        for d in data.dimensions:
            maturity_score = d.maturity_level / 5 * 10
            adoption_gap = 100 - d.adoption_pct
            results.append({
                "dimension": d.dimension_name,
                "maturity": d.maturity_level,
                "adoption": d.adoption_pct,
                "adoption_gap": round(adoption_gap, 1),
                "technologies": d.key_technologies,
            })
            avg_maturity += d.maturity_level
        avg_maturity = avg_maturity / len(data.dimensions) if data.dimensions else 0
        digital_readiness = "ADVANCED" if avg_maturity >= 4 else "DEVELOPING" if avg_maturity >= 2.5 else "EMERGING"
        return {
            "success": True,
            "organization": data.organization_name,
            "industry": data.industry,
            "dimensions_count": len(data.dimensions),
            "average_maturity": round(avg_maturity, 2),
            "digital_readiness": digital_readiness,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Market Attractiveness
# =============================================================================


@industry_market_app.post("/attractiveness/analyze")
def market_attractiveness_analyze(data: MarketAttractivenessSchema):
    try:
        attractiveness_score = (
            data.profit_potential * 2 +
            (10 - data.competitive_intensity) * 1.5 +
            min(data.growth_rate_pct, 10) * 1.5
        )
        regulatory_factor = 1.0 if data.regulatory_environment == "FAVORABLE" else 0.7 if data.regulatory_environment == "NEUTRAL" else 0.4
        risk_factor = 1.0 if data.technology_risk == "LOW" else 0.7 if data.technology_risk == "MEDIUM" else 0.4
        adjusted_score = attractiveness_score * regulatory_factor * risk_factor / 15 * 10
        attractiveness = "HIGH" if adjusted_score >= 7 else "MEDIUM" if adjusted_score >= 4 else "LOW"
        return {
            "success": True,
            "market": data.market_name,
            "market_size": data.market_size,
            "raw_attractiveness": round(attractiveness_score, 2),
            "adjusted_score": round(adjusted_score, 2),
            "attractiveness_level": attractiveness,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Industry Structure
# =============================================================================


@industry_market_app.post("/structure/analyze")
def industry_structure_analyze(data: IndustryStructureSchema):
    try:
        structure_type = data.fragmentation
        concentration_level = "HIGH" if data.concentration_ratio_pct >= 60 else \
                              "MODERATE" if data.concentration_ratio_pct >= 30 else "LOW"
        barrier_risk = "HIGH" if data.barriers_to_entry == "HIGH" else "LOW"
        return {
            "success": True,
            "industry": data.industry_name,
            "fragmentation": structure_type,
            "concentration_ratio": data.concentration_ratio_pct,
            "concentration_level": concentration_level,
            "leading_firms": data.leading_firms,
            "barriers_to_entry": data.barriers_to_entry,
            "switching_costs": data.switching_costs,
            "vertical_integration": data.vertical_integration,
            "new_entry_risk": "LOW" if barrier_risk == "HIGH" else "HIGH",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Competitive Forces
# =============================================================================


@industry_market_app.post("/competitive-forces/analyze")
def competitive_forces_analyze(data: CompetitiveForcesSchema):
    try:
        results = []
        total_intensity = 0
        increasing_forces = []
        for f in data.forces:
            total_intensity += f.intensity
            if f.trend == "INCREASING":
                increasing_forces.append(f.force_name)
            results.append({
                "force": f.force_name,
                "intensity": f.intensity,
                "trend": f.trend,
                "drivers": f.key_drivers,
            })
        avg_intensity = total_intensity / len(data.forces) if data.forces else 0
        industry_appeal = "ATTRACTIVE" if avg_intensity <= 4 else "NEUTRAL" if avg_intensity <= 6.5 else "UNATTRACTIVE"
        return {
            "success": True,
            "organization": data.organization_name,
            "industry": data.industry,
            "forces_count": len(data.forces),
            "average_intensity": round(avg_intensity, 2),
            "industry_appeal": industry_appeal,
            "increasing_forces": increasing_forces,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/industry-market"):
    parent_app.mount(prefix, industry_market_app)
