"""
Environmental Scanning Organ — FastAPI Router
BIO-ERP v5.3.0 — env_scanning_organ

10 technique endpoints with stateless engines.
"""

from fastapi import APIRouter
from datetime import datetime

from app.organs.env_scanning_organ.schemas import (
    PESTELAnalysisRequest,
    SWOTAnalysisRequest,
    ScenarioPlanningRequest,
    CompetitorIntelligenceRequest,
    CustomerAnalysisRequest,
    TrendAnalysisRequest,
    BenchmarkingRequest,
    MarketResearchRequest,
    StakeholderMappingRequest,
    EnvironmentalAssessmentRequest,
)
from app.organs.env_scanning_organ.services import (
    PESTELEngine,
    SWOTEngine,
    ScenarioPlanningEngine,
    CompetitorIntelligenceEngine,
    CustomerAnalysisEngine,
    TrendAnalysisEngine,
    BenchmarkingEngine,
    MarketResearchEngine,
    StakeholderMappingEngine,
    EnvironmentalAssessmentEngine,
)

router = APIRouter()


# =============================================================================
# ROOT & HEALTH
# =============================================================================


@router.get("/")
def root():
    return {
        "service": "Environmental Scanning & Analysis Microservice",
        "version": "5.3.0",
        "techniques_count": 10,
        "techniques": [
            "pestel-analysis",
            "swot-analysis",
            "scenario-planning",
            "competitor-intelligence",
            "customer-analysis",
            "trend-analysis",
            "benchmarking",
            "market-research",
            "stakeholder-mapping",
            "environmental-assessment",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health():
    return {
        "status": "healthy",
        "module": "env-scanning",
        "version": "5.3.0",
        "timestamp": datetime.now().isoformat(),
        "engines_ready": [
            "pestel",
            "swot",
            "scenario_planning",
            "competitor_intelligence",
            "customer_analysis",
            "trend_analysis",
            "benchmarking",
            "market_research",
            "stakeholder_mapping",
            "environmental_assessment",
        ],
    }


# =============================================================================
# 1. PESTEL ANALYSIS
# =============================================================================


@router.post("/pestel/analyze")
def pestel_analyze(req: PESTELAnalysisRequest):
    try:
        categories = {
            "political": [f.model_dump() for f in req.political],
            "economic": [f.model_dump() for f in req.economic],
            "social": [f.model_dump() for f in req.social],
            "technological": [f.model_dump() for f in req.technological],
            "environmental": [f.model_dump() for f in req.environmental],
            "legal": [f.model_dump() for f in req.legal],
        }
        result = PESTELEngine.analyze(categories)
        return {
            "success": True,
            "technique": "PESTEL",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 2. SWOT ANALYSIS
# =============================================================================


@router.post("/swot/analyze")
def swot_analyze(req: SWOTAnalysisRequest):
    try:
        result = SWOTEngine.analyze(
            [s.model_dump() for s in req.strengths],
            [w.model_dump() for w in req.weaknesses],
            [o.model_dump() for o in req.opportunities],
            [t.model_dump() for t in req.threats],
        )
        return {
            "success": True,
            "technique": "SWOT",
            "organization": req.organization,
            "result": result,
            "interpretation": result["position_description"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 3. SCENARIO PLANNING
# =============================================================================


@router.post("/scenario/analyze")
def scenario_analyze(req: ScenarioPlanningRequest):
    try:
        scenarios_data = [s.model_dump() for s in req.scenarios]
        result = ScenarioPlanningEngine.analyze(
            req.uncertainty_x,
            req.uncertainty_y,
            scenarios_data,
            req.planning_horizon_years,
        )
        interp = (
            f"Risk assessment: {result['risk_assessment']}. "
            f"Expected impact: {result['expected_impact_score']}. "
            f"Best case: {result['best_case']}. Worst case: {result['worst_case']}."
        )
        return {
            "success": True,
            "technique": "SCENARIO_PLANNING",
            "organization": req.organization,
            "result": result,
            "interpretation": interp,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 4. COMPETITOR INTELLIGENCE
# =============================================================================


@router.post("/competitor/analyze")
def competitor_analyze(req: CompetitorIntelligenceRequest):
    try:
        our_scores = {
            "price_score": req.our_price_score,
            "quality_score": req.our_quality_score,
            "innovation_score": req.our_innovation_score,
            "market_presence_score": req.our_market_presence_score,
        }
        result = CompetitorIntelligenceEngine.analyze(
            our_scores, [c.model_dump() for c in req.competitors],
        )
        interp = (
            f"Our composite: {result['our_composite_score']}. "
            f"High threats: {result['high_threat_competitors']}. "
            f"Market concentration: {result['market_concentration']}%."
        )
        return {
            "success": True,
            "technique": "COMPETITOR_INTELLIGENCE",
            "organization": req.organization,
            "result": result,
            "interpretation": interp,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 5. CUSTOMER ANALYSIS
# =============================================================================


@router.post("/customer/analyze")
def customer_analyze(req: CustomerAnalysisRequest):
    try:
        result = CustomerAnalysisEngine.analyze(
            [s.model_dump() for s in req.segments],
            req.discount_rate_pct,
        )
        interp = (
            f"Best segment: {result['best_segment']}. "
            f"High-priority segments: {result['high_priority_count']}. "
            f"Weighted growth: {result['weighted_avg_growth_pct']}%."
        )
        return {
            "success": True,
            "technique": "CUSTOMER_ANALYSIS",
            "organization": req.organization,
            "result": result,
            "interpretation": interp,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 6. TREND ANALYSIS
# =============================================================================


@router.post("/trend/analyze")
def trend_analyze(req: TrendAnalysisRequest):
    try:
        result = TrendAnalysisEngine.analyze(
            [dp.model_dump() for dp in req.data_points],
            req.forecast_periods,
        )
        interp = (
            f"Trend: {result['trend_direction']}. "
            f"Slope: {result['slope']}. "
            f"R-squared: {result['r_squared']}. "
            f"Forecast quality: {result['forecast_quality']}."
        )
        return {
            "success": True,
            "technique": "TREND_ANALYSIS",
            "organization": req.organization,
            "result": result,
            "interpretation": interp,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 7. BENCHMARKING
# =============================================================================


@router.post("/benchmarking/analyze")
def benchmarking_analyze(req: BenchmarkingRequest):
    try:
        result = BenchmarkingEngine.analyze([m.model_dump() for m in req.metrics])
        interp = (
            f"Overall position: {result['overall_position']}. "
            f"Above benchmark: {result['above_benchmark_count']}. "
            f"Below benchmark: {result['below_benchmark_count']}. "
            f"Urgent improvements: {result['urgent_improvements']}."
        )
        return {
            "success": True,
            "technique": "BENCHMARKING",
            "organization": req.organization,
            "result": result,
            "interpretation": interp,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 8. MARKET RESEARCH
# =============================================================================


@router.post("/market-research/analyze")
def market_research_analyze(req: MarketResearchRequest):
    try:
        result = MarketResearchEngine.analyze(req.model_dump())
        interp = (
            f"Attractiveness: {result['attractiveness_rating']} "
            f"(score: {result['market_attractiveness_score']}). "
            f"Entry feasibility: {result['entry_feasibility']}. "
            f"Strategy: {result['recommended_entry_strategy']}."
        )
        return {
            "success": True,
            "technique": "MARKET_RESEARCH",
            "organization": req.organization,
            "result": result,
            "interpretation": interp,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 9. STAKEHOLDER MAPPING
# =============================================================================


@router.post("/stakeholder/analyze")
def stakeholder_analyze(req: StakeholderMappingRequest):
    try:
        result = StakeholderMappingEngine.analyze(
            [s.model_dump() for s in req.stakeholders],
        )
        interp = (
            f"Total stakeholders: {result['stakeholder_count']}. "
            f"Risk indicator: {result['risk_indicator']}. "
            f"Critical zone: {result['summary']['critical_stakeholders']}."
        )
        return {
            "success": True,
            "technique": "STAKEHOLDER_MAPPING",
            "organization": req.organization,
            "result": result,
            "interpretation": interp,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 10. ENVIRONMENTAL ASSESSMENT
# =============================================================================


@router.post("/assessment/analyze")
def environmental_assessment_analyze(req: EnvironmentalAssessmentRequest):
    try:
        result = EnvironmentalAssessmentEngine.analyze(req.model_dump())
        interp = (
            f"Health: {result['health_rating']} "
            f"(score: {result['environmental_health_score']}). "
            f"{result['health_description']}"
        )
        return {
            "success": True,
            "technique": "ENVIRONMENTAL_ASSESSMENT",
            "organization": req.organization,
            "result": result,
            "interpretation": interp,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}
