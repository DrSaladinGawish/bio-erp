from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter

from app.organs.strategic_performance_organ.schemas import (
    BSCScorecardRequest,
    EFQMAssessmentRequest,
    TQMAssessmentRequest,
    KPIFrameworkRequest,
    PerformanceDashboardRequest,
    BenchmarkingRequest,
    StrategyMapRequest,
    PerformanceContractRequest,
    OKRCascadingRequest,
    PerformanceReviewRequest,
    GapAnalysisRequest,
    ImprovementPlanRequest,
    BSCVarianceRequest,
    MeasurementSystemRequest,
    RBMEvaluationRequest,
)
from app.organs.strategic_performance_organ.services import StrategicPerformanceService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["strategic-performance"])

svc = StrategicPerformanceService()


# =============================================================================
# Root & Health
# =============================================================================


@router.get("/")
def root():
    return {
        "service": "Strategic Performance Measurement Organ",
        "version": "1.0.0",
        "techniques_count": 15,
        "techniques": [
            "Balanced Scorecard (BSC)",
            "EFQM Excellence Model",
            "Total Quality Management (TQM)",
            "KPI Frameworks",
            "Performance Dashboards",
            "Benchmarking",
            "Strategy Maps",
            "Performance Contracts",
            "OKR Cascading",
            "Performance Reviews",
            "Gap Analysis",
            "Improvement Plans",
            "Balanced Scorecard Variance",
            "Performance Measurement Systems",
            "Results-Based Management",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "organ": "strategic-performance",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "engines_ready": [
            "bsc",
            "efqm",
            "tqm",
            "kpi_framework",
            "dashboard",
            "benchmarking",
            "strategy_map",
            "performance_contract",
            "okr_cascading",
            "performance_review",
            "gap_analysis",
            "improvement_plan",
            "bsc_variance",
            "measurement_system",
            "rbm",
        ],
    }


# =============================================================================
# 1. Balanced Scorecard (BSC)
# =============================================================================


@router.post("/bsc/scorecard")
async def bsc_scorecard(req: BSCScorecardRequest):
    try:
        result = svc.bsc.calculate_scorecard(
            [p.model_dump() for p in req.perspectives],
            req.measurement_period,
        )
        logger.info("BSC scorecard calculated: period=%s", req.measurement_period)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("BSC scorecard error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 2. EFQM Excellence Model
# =============================================================================


@router.post("/efqm/assessment")
async def efqm_assessment(req: EFQMAssessmentRequest):
    try:
        result = svc.efqm.assess([c.model_dump() for c in req.criteria])
        result["organization"] = req.organization_name
        logger.info("EFQM assessment completed: org=%s", req.organization_name)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("EFQM assessment error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 3. Total Quality Management (TQM)
# =============================================================================


@router.post("/tqm/assessment")
async def tqm_assessment(req: TQMAssessmentRequest):
    try:
        result = svc.tqm.assess([p.model_dump() for p in req.pillars])
        result["organization"] = req.organization_name
        logger.info("TQM assessment completed: org=%s", req.organization_name)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("TQM assessment error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 4. KPI Frameworks
# =============================================================================


@router.post("/kpi/framework")
async def kpi_framework(req: KPIFrameworkRequest):
    try:
        result = svc.kpi.analyze([k.model_dump() for k in req.kpis], req.framework)
        logger.info(
            "KPI framework analyzed: framework=%s, kpis=%d",
            req.framework,
            len(req.kpis),
        )
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("KPI framework error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 5. Performance Dashboards
# =============================================================================


@router.post("/dashboard/summary")
async def performance_dashboard(req: PerformanceDashboardRequest):
    try:
        result = svc.dashboard.aggregate(
            [m.model_dump() for m in req.metrics],
            req.time_period,
            req.comparison_baseline,
        )
        logger.info("Dashboard aggregated: metrics=%d", len(req.metrics))
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Dashboard error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 6. Benchmarking
# =============================================================================


@router.post("/benchmark/compare")
async def benchmark_compare(req: BenchmarkingRequest):
    try:
        result = svc.benchmarking.compare(
            [m.model_dump() for m in req.metrics],
            req.benchmark_source,
        )
        result["organization"] = req.organization_name
        logger.info("Benchmarking completed: org=%s", req.organization_name)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Benchmarking error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 7. Strategy Maps
# =============================================================================


@router.post("/strategy-map")
async def strategy_map(req: StrategyMapRequest):
    try:
        result = svc.strategy_map.build_map(
            [n.model_dump() for n in req.nodes],
            req.strategy_name,
        )
        logger.info(
            "Strategy map built: strategy=%s, nodes=%d",
            req.strategy_name,
            len(req.nodes),
        )
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Strategy map error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 8. Performance Contracts
# =============================================================================


@router.post("/contract/evaluate")
async def performance_contract(req: PerformanceContractRequest):
    try:
        result = svc.contract.evaluate_contract(
            req.employee_id,
            req.employee_name,
            req.review_period,
            [k.model_dump() for k in req.kpis],
        )
        logger.info("Performance contract evaluated: employee=%s", req.employee_id)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Performance contract error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 9. OKR Cascading
# =============================================================================


@router.post("/okr/cascade")
async def okr_cascading(req: OKRCascadingRequest):
    try:
        result = svc.okr.cascade(
            [o.model_dump() for o in req.company_okrs],
            [o.model_dump() for o in req.department_okrs],
            [o.model_dump() for o in req.team_okrs],
            req.quarter,
        )
        logger.info("OKR cascading completed: quarter=%s", req.quarter)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("OKR cascading error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 10. Performance Reviews
# =============================================================================


@router.post("/review/score")
async def performance_review(req: PerformanceReviewRequest):
    try:
        result = svc.review.review(
            [m.model_dump() for m in req.metrics],
            req.entity_id,
            req.entity_type,
            req.period,
        )
        logger.info("Performance review completed: entity=%s", req.entity_id)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Performance review error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 11. Gap Analysis
# =============================================================================


@router.post("/gap/analysis")
async def gap_analysis(req: GapAnalysisRequest):
    try:
        result = svc.gap.analyze(
            [m.model_dump() for m in req.metrics],
            req.target_date,
        )
        logger.info("Gap analysis completed: metrics=%d", len(req.metrics))
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Gap analysis error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 12. Improvement Plans
# =============================================================================


@router.post("/improvement/plan")
async def improvement_plan(req: ImprovementPlanRequest):
    try:
        result = svc.improvement.plan(
            req.area,
            req.current_score,
            req.target_score,
            [a.model_dump() for a in req.actions],
            req.timeline,
        )
        logger.info("Improvement plan created: area=%s", req.area)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Improvement plan error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 13. Balanced Scorecard Variance
# =============================================================================


@router.post("/bsc/variance")
async def bsc_variance(req: BSCVarianceRequest):
    try:
        result = svc.bsc_variance.analyze(
            [m.model_dump() for m in req.metrics],
            req.period,
        )
        logger.info("BSC variance analysis: period=%s", req.period)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("BSC variance error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 14. Performance Measurement Systems
# =============================================================================


@router.post("/measurement-system/evaluate")
async def measurement_system(req: MeasurementSystemRequest):
    try:
        result = svc.measurement_system.evaluate(
            req.system_name,
            [f.model_dump() for f in req.frameworks],
        )
        logger.info("Measurement system evaluated: system=%s", req.system_name)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("Measurement system error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }


# =============================================================================
# 15. Results-Based Management
# =============================================================================


@router.post("/rbm/evaluate")
async def rbm_evaluate(req: RBMEvaluationRequest):
    try:
        result = svc.rbm.evaluate(
            req.program_name,
            [o.model_dump() for o in req.outcomes],
            req.budget_allocated,
            req.budget_spent,
        )
        logger.info("RBM evaluation completed: program=%s", req.program_name)
        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error("RBM evaluation error: %s", e)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }
