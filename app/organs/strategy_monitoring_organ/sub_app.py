"""
Strategy Monitoring & Control Sub-Application for BIO-ERP v5
============================================================
Mount at: app.mount("/api/v1/strategy-monitoring", strategy_monitoring_app) in BIO-ERP's main.py

Techniques: Variance Analysis, KPI Dashboards, Strategy Review, Early Warning Systems,
            Performance Monitoring, Strategic Audit
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

strategy_monitoring_app = FastAPI(
    title="Strategy Monitoring & Control Microservice",
    description="Strategy Monitoring & Control — Variance Analysis, KPI Dashboards, Strategy Review, Early Warning, Performance Monitoring, Strategic Audit",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — Variance Analysis
# =============================================================================


class VarianceMetricSchema(BaseModel):
    metric_name: str = Field(..., min_length=1)
    planned_value: float = Field(...)
    actual_value: float = Field(...)
    unit: str = Field(default="")
    tolerance_pct: float = Field(default=10.0, ge=0, le=100)


class VarianceAnalysisSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    period: str = Field(default="Q1-2026")
    metrics: List[VarianceMetricSchema]

# =============================================================================
# PYDANTIC SCHEMAS — KPI Dashboard
# =============================================================================


class KPIEntrySchema(BaseModel):
    kpi_name: str = Field(..., min_length=1)
    current_value: float = Field(...)
    target_value: float = Field(...)
    previous_value: float = Field(default=0.0)
    unit: str = Field(default="")
    category: str = Field(default="FINANCIAL")


class KPIDashboardSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    period: str = Field(default="Q1-2026")
    kpis: List[KPIEntrySchema]

# =============================================================================
# PYDANTIC SCHEMAS — Strategy Review
# =============================================================================


class StrategyReviewItemSchema(BaseModel):
    objective_name: str = Field(..., min_length=1)
    status: str = Field(..., description="ON_TRACK, AT_RISK, BEHIND, COMPLETED")
    progress_pct: float = Field(default=0.0, ge=0, le=100)
    notes: str = Field(default="")
    corrective_action: str = Field(default="")


class StrategyReviewSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    review_date: str = Field(default="")
    items: List[StrategyReviewItemSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Early Warning Systems
# =============================================================================


class WarningIndicatorSchema(BaseModel):
    indicator_name: str = Field(..., min_length=1)
    current_value: float = Field(...)
    threshold_green: float = Field(...)
    threshold_amber: float = Field(...)
    threshold_red: float = Field(...)
    trend: str = Field(default="STABLE", description="IMPROVING, STABLE, DECLINING")


class EarlyWarningSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    indicators: List[WarningIndicatorSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Performance Monitoring
# =============================================================================


class PerformanceMetricSchema(BaseModel):
    metric_name: str = Field(..., min_length=1)
    actual: float = Field(...)
    target: float = Field(...)
    baseline: float = Field(default=0.0)
    weight: float = Field(default=1.0, gt=0, le=10)
    category: str = Field(default="FINANCIAL")


class PerformanceMonitoringSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    period: str = Field(default="Q1-2026")
    metrics: List[PerformanceMetricSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Strategic Audit
# =============================================================================


class AuditAreaSchema(BaseModel):
    area_name: str = Field(..., min_length=1)
    compliance_score: float = Field(default=5.0, ge=1, le=10)
    effectiveness_score: float = Field(default=5.0, ge=1, le=10)
    findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class StrategicAuditSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    audit_scope: str = Field(default="FULL")
    areas: List[AuditAreaSchema]

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@strategy_monitoring_app.get("/")
def root():
    return {
        "service": "Strategy Monitoring & Control Microservice",
        "version": "1.0.0",
        "techniques": [
            "Variance_Analysis", "KPI_Dashboards", "Strategy_Review",
            "Early_Warning_Systems", "Performance_Monitoring", "Strategic_Audit",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@strategy_monitoring_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "strategy-monitoring",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "variance_analysis", "kpi_dashboards", "strategy_review",
            "early_warning", "performance_monitoring", "strategic_audit",
        ],
    }

# =============================================================================
# ENDPOINTS — Variance Analysis
# =============================================================================


@strategy_monitoring_app.post("/variance/analyze")
def variance_analyze(analysis: VarianceAnalysisSchema):
    try:
        results = []
        favorable_count = 0
        unfavorable_count = 0
        for m in analysis.metrics:
            variance = m.actual_value - m.planned_value
            variance_pct = (variance / abs(m.planned_value) * 100) if m.planned_value != 0 else 0
            within_tolerance = abs(variance_pct) <= m.tolerance_pct
            status = "FAVORABLE" if variance > 0 else "UNFAVORABLE" if variance < 0 else "ON_TARGET"
            if status == "FAVORABLE":
                favorable_count += 1
            elif status == "UNFAVORABLE":
                unfavorable_count += 1
            results.append({
                "metric": m.metric_name,
                "planned": m.planned_value,
                "actual": m.actual_value,
                "variance": round(variance, 2),
                "variance_pct": round(variance_pct, 2),
                "within_tolerance": within_tolerance,
                "status": status,
            })
        return {
            "success": True,
            "organization": analysis.organization_name,
            "period": analysis.period,
            "total_metrics": len(analysis.metrics),
            "favorable": favorable_count,
            "unfavorable": unfavorable_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — KPI Dashboard
# =============================================================================


@strategy_monitoring_app.post("/kpi/dashboard")
def kpi_dashboard(dashboard: KPIDashboardSchema):
    try:
        results = []
        total_progress = 0
        for kpi in dashboard.kpis:
            progress = (kpi.current_value / kpi.target_value * 100) if kpi.target_value != 0 else 0
            change = kpi.current_value - kpi.previous_value
            change_pct = (change / abs(kpi.previous_value) * 100) if kpi.previous_value != 0 else 0
            status = "GREEN" if progress >= 90 else "AMBER" if progress >= 70 else "RED"
            total_progress += min(progress, 150)
            results.append({
                "kpi": kpi.kpi_name,
                "category": kpi.category,
                "current": kpi.current_value,
                "target": kpi.target_value,
                "progress_pct": round(progress, 1),
                "change_pct": round(change_pct, 1),
                "status": status,
            })
        avg_progress = total_progress / len(dashboard.kpis) if dashboard.kpis else 0
        return {
            "success": True,
            "organization": dashboard.organization_name,
            "period": dashboard.period,
            "kpi_count": len(dashboard.kpis),
            "average_progress": round(avg_progress, 1),
            "green_count": len([r for r in results if r["status"] == "GREEN"]),
            "amber_count": len([r for r in results if r["status"] == "AMBER"]),
            "red_count": len([r for r in results if r["status"] == "RED"]),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategy Review
# =============================================================================


@strategy_monitoring_app.post("/review/analyze")
def strategy_review_analyze(review: StrategyReviewSchema):
    try:
        status_counts = {}
        for item in review.items:
            status_counts[item.status] = status_counts.get(item.status, 0) + 1
        total = len(review.items)
        avg_progress = sum(item.progress_pct for item in review.items) / total if total else 0
        behind_items = [item for item in review.items if item.status in ("BEHIND", "AT_RISK")]
        actions_needed = [item.corrective_action for item in behind_items if item.corrective_action]
        return {
            "success": True,
            "organization": review.organization_name,
            "total_objectives": total,
            "status_distribution": status_counts,
            "average_progress_pct": round(avg_progress, 1),
            "items_requiring_action": len(behind_items),
            "corrective_actions": actions_needed,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Early Warning Systems
# =============================================================================


@strategy_monitoring_app.post("/warning/evaluate")
def early_warning_evaluate(warnings: EarlyWarningSchema):
    try:
        results = []
        red_count = 0
        amber_count = 0
        green_count = 0
        for ind in warnings.indicators:
            if ind.current_value <= ind.threshold_red:
                level = "RED"
                red_count += 1
            elif ind.current_value <= ind.threshold_amber:
                level = "AMBER"
                amber_count += 1
            else:
                level = "GREEN"
                green_count += 1
            results.append({
                "indicator": ind.indicator_name,
                "value": ind.current_value,
                "level": level,
                "trend": ind.trend,
            })
        overall = "CRITICAL" if red_count > 0 else "WARNING" if amber_count > 0 else "HEALTHY"
        return {
            "success": True,
            "organization": warnings.organization_name,
            "total_indicators": len(warnings.indicators),
            "green": green_count,
            "amber": amber_count,
            "red": red_count,
            "overall_status": overall,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Performance Monitoring
# =============================================================================


@strategy_monitoring_app.post("/performance/analyze")
def performance_analyze(monitoring: PerformanceMonitoringSchema):
    try:
        weighted_total = 0
        total_weight = 0
        results = []
        for m in monitoring.metrics:
            progress = (m.actual / m.target * 100) if m.target != 0 else 0
            weighted_total += min(progress, 150) * m.weight
            total_weight += m.weight
            results.append({
                "metric": m.metric_name,
                "actual": m.actual,
                "target": m.target,
                "progress_pct": round(progress, 1),
                "category": m.category,
                "status": "ON_TRACK" if progress >= 90 else "AT_RISK" if progress >= 70 else "BEHIND",
            })
        overall_score = weighted_total / total_weight if total_weight > 0 else 0
        return {
            "success": True,
            "organization": monitoring.organization_name,
            "period": monitoring.period,
            "metrics_count": len(monitoring.metrics),
            "overall_score": round(overall_score, 1),
            "on_track": len([r for r in results if r["status"] == "ON_TRACK"]),
            "at_risk": len([r for r in results if r["status"] == "AT_RISK"]),
            "behind": len([r for r in results if r["status"] == "BEHIND"]),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategic Audit
# =============================================================================


@strategy_monitoring_app.post("/audit/analyze")
def strategic_audit_analyze(audit: StrategicAuditSchema):
    try:
        results = []
        total_findings = 0
        total_recommendations = 0
        for area in audit.areas:
            avg_score = (area.compliance_score + area.effectiveness_score) / 2
            status = "STRONG" if avg_score >= 8 else "ADEQUATE" if avg_score >= 5 else "WEAK"
            total_findings += len(area.findings)
            total_recommendations += len(area.recommendations)
            results.append({
                "area": area.area_name,
                "compliance": area.compliance_score,
                "effectiveness": area.effectiveness_score,
                "average_score": round(avg_score, 2),
                "status": status,
                "findings_count": len(area.findings),
            })
        overall_compliance = sum(a.compliance_score for a in audit.areas) / len(audit.areas) if audit.areas else 0
        return {
            "success": True,
            "organization": audit.organization_name,
            "scope": audit.audit_scope,
            "areas_count": len(audit.areas),
            "overall_compliance": round(overall_compliance, 2),
            "total_findings": total_findings,
            "total_recommendations": total_recommendations,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/strategy-monitoring"):
    parent_app.mount(prefix, strategy_monitoring_app)
