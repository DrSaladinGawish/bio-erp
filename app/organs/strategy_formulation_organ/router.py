"""
Strategy Formulation Organ — FastAPI Router
BIO-ERP v5.3.0 — strategy_formulation_organ

12 technique endpoints backed by stateless engines.
"""

from fastapi import APIRouter
from datetime import datetime

from app.organs.strategy_formulation_organ.schemas import (
    BCGMatrixRequest,
    AnsoffRequest,
    BlueOceanRequest,
    PorterGenericRequest,
    TOWSRequest,
    CompetitiveAdvantageRequest,
    CoreCompetencyRequest,
    StrategicIntentRequest,
    ValueInnovationRequest,
    DisruptiveInnovationRequest,
    PlatformStrategyRequest,
    EcosystemStrategyRequest,
)
from app.organs.strategy_formulation_organ.services import (
    BCGEngine,
    AnsoffEngine,
    BlueOceanEngine,
    PorterGenericEngine,
    TOWSEngine,
    CompetitiveAdvantageEngine,
    CoreCompetencyEngine,
    StrategicIntentEngine,
    ValueInnovationEngine,
    DisruptiveInnovationEngine,
    PlatformStrategyEngine,
    EcosystemStrategyEngine,
)

router = APIRouter()


# =============================================================================
# ROOT & HEALTH
# =============================================================================


@router.get("/")
def root():
    return {
        "service": "Strategy Formulation Microservice",
        "version": "5.3.0",
        "techniques_count": 12,
        "techniques": [
            "bcg-matrix",
            "ansoff-matrix",
            "blue-ocean-strategy",
            "porters-generic-strategies",
            "tows-strategy",
            "competitive-advantage",
            "core-competency",
            "strategic-intent",
            "value-innovation",
            "disruptive-innovation",
            "platform-strategy",
            "ecosystem-strategy",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health():
    return {
        "status": "healthy",
        "module": "strategy-formulation",
        "version": "5.3.0",
        "timestamp": datetime.now().isoformat(),
        "engines_ready": [
            "bcg_matrix",
            "ansoff_matrix",
            "blue_ocean",
            "porters_generic",
            "tows_strategy",
            "competitive_advantage",
            "core_competency",
            "strategic_intent",
            "value_innovation",
            "disruptive_innovation",
            "platform_strategy",
            "ecosystem_strategy",
        ],
    }


# =============================================================================
# 1. BCG MATRIX
# =============================================================================


@router.post("/bcg/analyze")
async def bcg_analyze(req: BCGMatrixRequest):
    try:
        units = [u.model_dump() for u in req.business_units]
        result = BCGEngine.analyze(units)
        return {
            "success": True,
            "technique": "BCG_MATRIX",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 2. ANSOFF MATRIX
# =============================================================================


@router.post("/ansoff/analyze")
async def ansoff_analyze(req: AnsoffRequest):
    try:
        result = AnsoffEngine.analyze(
            [p.model_dump() for p in req.products],
            [m.model_dump() for m in req.markets],
            req.current_state.model_dump(),
        )
        return {
            "success": True,
            "technique": "ANSOFF_MATRIX",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 3. BLUE OCEAN STRATEGY
# =============================================================================


@router.post("/blue-ocean/analyze")
async def blue_ocean_analyze(req: BlueOceanRequest):
    try:
        result = BlueOceanEngine.analyze(
            [f.model_dump() for f in req.factors],
            [c.model_dump() for c in req.competitor_factors],
        )
        return {
            "success": True,
            "technique": "BLUE_OCEAN",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 4. PORTER'S GENERIC STRATEGIES
# =============================================================================


@router.post("/porters-generic/analyze")
async def porters_generic_analyze(req: PorterGenericRequest):
    try:
        result = PorterGenericEngine.analyze(
            req.cost_position,
            [d.model_dump() for d in req.differentiation_strengths],
            req.market_scope,
            req.competitive_scope,
        )
        return {
            "success": True,
            "technique": "PORTERS_GENERIC",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 5. TOWS STRATEGY
# =============================================================================


@router.post("/tows/analyze")
async def tows_analyze(req: TOWSRequest):
    try:
        result = TOWSEngine.analyze(
            [s.model_dump() for s in req.strengths],
            [w.model_dump() for w in req.weaknesses],
            [o.model_dump() for o in req.opportunities],
            [t.model_dump() for t in req.threats],
        )
        return {
            "success": True,
            "technique": "TOWS_STRATEGY",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 6. COMPETITIVE ADVANTAGE
# =============================================================================


@router.post("/competitive-advantage/analyze")
async def competitive_advantage_analyze(req: CompetitiveAdvantageRequest):
    try:
        result = CompetitiveAdvantageEngine.analyze(
            [a.model_dump() for a in req.advantages]
        )
        return {
            "success": True,
            "technique": "COMPETITIVE_ADVANTAGE",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 7. CORE COMPETENCY
# =============================================================================


@router.post("/core-competency/analyze")
async def core_competency_analyze(req: CoreCompetencyRequest):
    try:
        result = CoreCompetencyEngine.analyze(
            [c.model_dump() for c in req.competencies]
        )
        return {
            "success": True,
            "technique": "CORE_COMPETENCY",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 8. STRATEGIC INTENT
# =============================================================================


@router.post("/strategic-intent/analyze")
async def strategic_intent_analyze(req: StrategicIntentRequest):
    try:
        result = StrategicIntentEngine.analyze(
            req.vision,
            req.mission,
            [o.model_dump() for o in req.objectives],
            req.current_performance,
            req.gap_to_ambition_pct,
        )
        return {
            "success": True,
            "technique": "STRATEGIC_INTENT",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 9. VALUE INNOVATION
# =============================================================================


@router.post("/value-innovation/analyze")
async def value_innovation_analyze(req: ValueInnovationRequest):
    try:
        result = ValueInnovationEngine.analyze(
            [e.model_dump() for e in req.value_elements],
            [b.model_dump() for b in req.competitor_benchmark],
        )
        return {
            "success": True,
            "technique": "VALUE_INNOVATION",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 10. DISRUPTIVE INNOVATION
# =============================================================================


@router.post("/disruptive-innovation/analyze")
async def disruptive_innovation_analyze(req: DisruptiveInnovationRequest):
    try:
        result = DisruptiveInnovationEngine.analyze(
            [s.model_dump() for s in req.market_segments]
        )
        return {
            "success": True,
            "technique": "DISRUPTIVE_INNOVATION",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 11. PLATFORM STRATEGY
# =============================================================================


@router.post("/platform-strategy/analyze")
async def platform_strategy_analyze(req: PlatformStrategyRequest):
    try:
        result = PlatformStrategyEngine.analyze(
            req.platform_type,
            req.network_effects.model_dump(),
            req.switching_costs,
            [p.model_dump() for p in req.ecosystem_partners],
        )
        return {
            "success": True,
            "technique": "PLATFORM_STRATEGY",
            "organization": None,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}


# =============================================================================
# 12. ECOSYSTEM STRATEGY
# =============================================================================


@router.post("/ecosystem-strategy/analyze")
async def ecosystem_strategy_analyze(req: EcosystemStrategyRequest):
    try:
        result = EcosystemStrategyEngine.analyze(
            [a.model_dump() for a in req.actors]
        )
        return {
            "success": True,
            "technique": "ECOSYSTEM_STRATEGY",
            "organization": req.organization,
            "result": result,
            "interpretation": result["interpretation"],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e), "timestamp": datetime.now().isoformat()}
