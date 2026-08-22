"""
Global & International Strategy Sub-Application for BIO-ERP v5
===============================================================
Mount at: app.mount("/api/v1/global-international", global_international_app) in BIO-ERP's main.py

Techniques: GLOBE Framework, CAGE Distance Framework, International Business Framework,
            Global Strategy, Multinational Strategy, Cross-Cultural Management, International Market Entry
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

global_international_app = FastAPI(
    title="Global & International Strategy Microservice",
    description="Global & International Strategy — GLOBE, CAGE, International Business, Cross-Cultural, Market Entry",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — GLOBE Framework
# =============================================================================


class GLOBEDimensionSchema(BaseModel):
    dimension_name: str = Field(..., min_length=1)
    culture_score: float = Field(default=5.0, ge=1, le=10)
    leadership_score: float = Field(default=5.0, ge=1, le=10)
    importance: float = Field(default=5.0, ge=1, le=10)


class GLOBEFrameworkSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    country: str = Field(default="")
    dimensions: List[GLOBEDimensionSchema]

# =============================================================================
# PYDANTIC SCHEMAS — CAGE Distance Framework
# =============================================================================


class CAGEDistanceSchema(BaseModel):
    home_country: str = Field(..., min_length=1)
    target_country: str = Field(..., min_length=1)
    cultural_distance: float = Field(default=5.0, ge=1, le=10)
    administrative_distance: float = Field(default=5.0, ge=1, le=10)
    geographic_distance: float = Field(default=5.0, ge=1, le=10)
    economic_distance: float = Field(default=5.0, ge=1, le=10)

# =============================================================================
# PYDANTIC SCHEMAS — International Business Framework
# =============================================================================


class IBFMarketSchema(BaseModel):
    market_name: str = Field(..., min_length=1)
    market_size: float = Field(default=0.0, ge=0)
    growth_rate_pct: float = Field(default=0.0)
    political_risk: float = Field(default=5.0, ge=1, le=10)
    economic_risk: float = Field(default=5.0, ge=1, le=10)
    ease_of_business: float = Field(default=5.0, ge=1, le=10)


class IBFSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    markets: List[IBFMarketSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Global/Multinational Strategy
# =============================================================================


class GlobalStrategySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    strategy_type: str = Field(..., description="GLOBAL, MULTIDOMESTIC, TRANSNATIONAL, INTERNATIONAL")
    home_market_share_pct: float = Field(default=0.0, ge=0, le=100)
    target_markets: List[str] = Field(default_factory=list)
    standardization_level: float = Field(default=5.0, ge=1, le=10, description="1=Fully Local, 10=Fully Standardized")
    local_responsiveness: float = Field(default=5.0, ge=1, le=10, description="1=Low, 10=High")

# =============================================================================
# PYDANTIC SCHEMAS — Cross-Cultural Management
# =============================================================================


class CulturalDimensionSchema(BaseModel):
    dimension_name: str = Field(..., min_length=1)
    home_score: float = Field(default=5.0, ge=1, le=10)
    host_score: float = Field(default=5.0, ge=1, le=10)
    management_implication: str = Field(default="")


class CrossCulturalSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    home_country: str = Field(...)
    host_country: str = Field(...)
    dimensions: List[CulturalDimensionSchema]

# =============================================================================
# PYDANTIC SCHEMAS — International Market Entry
# =============================================================================


class IntlEntryModeSchema(BaseModel):
    mode_name: str = Field(..., min_length=1)
    market_name: str = Field(..., min_length=1)
    entry_type: str = Field(..., description="EXPORT, LICENSING, FRANCHISING, JV, WHOLLY_OWNED")
    control_level: float = Field(default=5.0, ge=1, le=10)
    resource_commitment: float = Field(default=5.0, ge=1, le=10)
    risk_level: float = Field(default=5.0, ge=1, le=10)
    expected_revenue: float = Field(default=0.0, ge=0)


class IntlMarketEntrySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    modes: List[IntlEntryModeSchema]

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@global_international_app.get("/")
def root():
    return {
        "service": "Global & International Strategy Microservice",
        "version": "1.0.0",
        "techniques": [
            "GLOBE_Framework", "CAGE_Distance", "International_Business_Framework",
            "Global_Strategy", "Multinational_Strategy",
            "Cross_Cultural_Management", "International_Market_Entry",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@global_international_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "global-international",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "globe", "cage", "ibf", "global_strategy",
            "multinational", "cross_cultural", "market_entry",
        ],
    }

# =============================================================================
# ENDPOINTS — GLOBE Framework
# =============================================================================


@global_international_app.post("/globe/analyze")
def globe_analyze(data: GLOBEFrameworkSchema):
    try:
        avg_culture = sum(d.culture_score for d in data.dimensions) / len(data.dimensions) if data.dimensions else 0
        avg_leadership = sum(d.leadership_score for d in data.dimensions) / len(data.dimensions) if data.dimensions else 0
        gaps = [{"dim": d.dimension_name, "gap": round(d.culture_score - d.leadership_score, 2)} for d in data.dimensions]
        return {
            "success": True,
            "organization": data.organization_name,
            "country": data.country,
            "dimensions_count": len(data.dimensions),
            "average_culture_score": round(avg_culture, 2),
            "average_leadership_score": round(avg_leadership, 2),
            "culture_leadership_gaps": gaps,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — CAGE Distance Framework
# =============================================================================


@global_international_app.post("/cage/analyze")
def cage_analyze(data: CAGEDistanceSchema):
    try:
        distances = {
            "CULTURAL": data.cultural_distance,
            "ADMINISTRATIVE": data.administrative_distance,
            "GEOGRAPHIC": data.geographic_distance,
            "ECONOMIC": data.economic_distance,
        }
        total_distance = sum(distances.values())
        avg_distance = total_distance / len(distances)
        most_challenging = max(distances, key=distances.get)
        recommendation = "HIGH_COMMITMENT" if avg_distance <= 3 else "MODERATE_COMMITMENT" if avg_distance <= 6 else "CAUTIOUS_ENTRY"
        return {
            "success": True,
            "home_country": data.home_country,
            "target_country": data.target_country,
            "distances": distances,
            "total_distance": round(total_distance, 2),
            "average_distance": round(avg_distance, 2),
            "most_challenging_dimension": most_challenging,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — International Business Framework
# =============================================================================


@global_international_app.post("/ibf/analyze")
def ibf_analyze(data: IBFSchema):
    try:
        results = []
        for m in data.markets:
            attractiveness = m.market_size * m.growth_rate_pct / 100 * (10 - m.political_risk) / 10
            risk_profile = "LOW" if m.political_risk <= 3 and m.economic_risk <= 3 else "HIGH" if m.political_risk >= 7 or m.economic_risk >= 7 else "MEDIUM"
            results.append({
                "market": m.market_name,
                "size": m.market_size,
                "growth": m.growth_rate_pct,
                "attractiveness": round(attractiveness, 2),
                "risk_profile": risk_profile,
            })
        results.sort(key=lambda r: r["attractiveness"], reverse=True)
        return {
            "success": True,
            "organization": data.organization_name,
            "markets_count": len(data.markets),
            "results": results,
            "best_market": results[0]["market"] if results else None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Global/Multinational Strategy
# =============================================================================


@global_international_app.post("/global-strategy/evaluate")
def global_strategy_evaluate(data: GlobalStrategySchema):
    try:
        strategy_fit = "TRANSNATIONAL" if data.standardization_level >= 6 and data.local_responsiveness >= 6 else \
                       "GLOBAL" if data.standardization_level >= 7 else \
                       "MULTIDOMESTIC" if data.local_responsiveness >= 7 else "INTERNATIONAL"
        complexity = "HIGH" if len(data.target_markets) > 5 else "MEDIUM" if len(data.target_markets) > 2 else "LOW"
        return {
            "success": True,
            "organization": data.organization_name,
            "declared_strategy": data.strategy_type,
            "implied_strategy": strategy_fit,
            "strategy_aligned": data.strategy_type.upper() == strategy_fit,
            "home_market_share": data.home_market_share_pct,
            "target_markets_count": len(data.target_markets),
            "complexity": complexity,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Cross-Cultural Management
# =============================================================================


@global_international_app.post("/cross-cultural/analyze")
def cross_cultural_analyze(data: CrossCulturalSchema):
    try:
        gaps = []
        max_gap_dim = None
        max_gap = 0
        for d in data.dimensions:
            gap = abs(d.home_score - d.host_score)
            gaps.append({
                "dimension": d.dimension_name,
                "home": d.home_score,
                "host": d.host_score,
                "gap": round(gap, 2),
                "implication": d.management_implication,
            })
            if gap > max_gap:
                max_gap = gap
                max_gap_dim = d.dimension_name
        cultural_challenge = "HIGH" if max_gap > 5 else "MODERATE" if max_gap > 2 else "LOW"
        return {
            "success": True,
            "organization": data.organization_name,
            "home_country": data.home_country,
            "host_country": data.host_country,
            "dimensions_count": len(data.dimensions),
            "max_cultural_gap": round(max_gap, 2),
            "max_gap_dimension": max_gap_dim,
            "cultural_challenge_level": cultural_challenge,
            "gaps": gaps,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — International Market Entry
# =============================================================================


@global_international_app.post("/entry-mode/analyze")
def entry_mode_analyze(data: IntlMarketEntrySchema):
    try:
        results = []
        for mode in data.modes:
            risk_adjusted_return = mode.expected_revenue * (10 - mode.risk_level) / 10
            value_score = risk_adjusted_return * mode.control_level / 10
            results.append({
                "mode": mode.mode_name,
                "market": mode.market_name,
                "type": mode.entry_type,
                "control": mode.control_level,
                "risk_adjusted_return": round(risk_adjusted_return, 2),
                "value_score": round(value_score, 2),
            })
        results.sort(key=lambda r: r["value_score"], reverse=True)
        return {
            "success": True,
            "organization": data.organization_name,
            "modes_count": len(data.modes),
            "results": results,
            "recommended_mode": results[0]["mode"] if results else None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/global-international"):
    parent_app.mount(prefix, global_international_app)
