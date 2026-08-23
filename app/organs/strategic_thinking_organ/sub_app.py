"""
Strategic Thinking Tools Sub-Application for BIO-ERP v5
========================================================
Mount at: app.mount("/api/v1/strategic-thinking", strategic_thinking_app) in BIO-ERP's main.py

Techniques: First Principles Thinking, Systems Thinking, Mental Models, Scenario Planning,
            Design Thinking, Reverse Engineering, Strategic Foresight, Analogical Reasoning,
            Strategic Agility, Strategic Intuition
"""

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
import warnings

warnings.filterwarnings("ignore", message=".*protected namespace.*")

strategic_thinking_app = FastAPI(
    title="Strategic Thinking Tools Microservice",
    description="Strategic Thinking — First Principles, Systems Thinking, Mental Models, Design Thinking, Foresight, and more",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# PYDANTIC SCHEMAS — First Principles Thinking
# =============================================================================


class FirstPrincipleSchema(BaseModel):
    principle: str = Field(..., min_length=1)
    confidence: float = Field(default=5.0, ge=1, le=10)
    evidence: List[str] = Field(default_factory=list)
    assumptions_challenged: List[str] = Field(default_factory=list)


class FirstPrinciplesSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    problem_statement: str = Field(...)
    principles: List[FirstPrincipleSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Systems Thinking
# =============================================================================


class SystemElementSchema(BaseModel):
    element_name: str = Field(..., min_length=1)
    element_type: str = Field(..., description="STOCK, FLOW, VARIABLE, AUXILIARY")
    description: str = Field(default="")
    connections: List[str] = Field(default_factory=list)
    feedback_type: str = Field(default="NONE", description="POSITIVE, NEGATIVE, NONE")


class SystemsThinkingSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    system_name: str = Field(...)
    elements: List[SystemElementSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Mental Models
# =============================================================================


class MentalModelSchema(BaseModel):
    model_name: str = Field(..., min_length=1)
    model_type: str = Field(..., description="FRAMEWORK, PRINCIPLE, HEURISTIC, ANALOGY")
    description: str = Field(default="")
    applicability: str = Field(default="")
    confidence: float = Field(default=5.0, ge=1, le=10)


class MentalModelsSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    decision_context: str = Field(default="")
    models: List[MentalModelSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Design Thinking
# =============================================================================


class DesignThinkingPhaseSchema(BaseModel):
    phase_name: str = Field(..., description="EMPATHIZE, DEFINE, IDEATE, PROTOTYPE, TEST")
    activities: List[str] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list)
    completion_pct: float = Field(default=0.0, ge=0, le=100)


class DesignThinkingSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    challenge: str = Field(...)
    phases: List[DesignThinkingPhaseSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Strategic Foresight
# =============================================================================


class ForesightSignalSchema(BaseModel):
    signal_name: str = Field(..., min_length=1)
    signal_type: str = Field(..., description="DRIVER, TREND, WILDCARD, MEGA_TREND")
    strength: float = Field(default=5.0, ge=1, le=10)
    timeframe_years: int = Field(default=5, ge=1, le=30)
    impact_areas: List[str] = Field(default_factory=list)


class StrategicForesightSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    horizon_years: int = Field(default=5, ge=1, le=30)
    signals: List[ForesightSignalSchema]

# =============================================================================
# PYDANTIC SCHEMAS — Analogical Reasoning
# =============================================================================


class AnalogySchema(BaseModel):
    source_domain: str = Field(..., min_length=1)
    target_domain: str = Field(..., min_length=1)
    similarity_score: float = Field(default=5.0, ge=1, le=10)
    key_insights: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class AnalogicalReasoningSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    problem_context: str = Field(default="")
    analogies: List[AnalogySchema]

# =============================================================================
# PYDANTIC SCHEMAS — Strategic Agility
# =============================================================================


class AgilityDimensionSchema(BaseModel):
    dimension_name: str = Field(..., min_length=1)
    current_score: float = Field(default=5.0, ge=1, le=10)
    target_score: float = Field(default=7.0, ge=1, le=10)
    weight: float = Field(default=1.0, gt=0, le=10)


class StrategicAgilitySchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    dimensions: List[AgilityDimensionSchema]
    response_time_target_days: int = Field(default=30, ge=1, le=365)

# =============================================================================
# PYDANTIC SCHEMAS — Strategic Intuition
# =============================================================================


class IntuitionInsightSchema(BaseModel):
    insight_name: str = Field(..., min_length=1)
    source: str = Field(default="EXPERIENCE", description="EXPERIENCE, PATTERN_RECOGNITION, GUT_FEEL, DATA_INTEGRATION")
    confidence: float = Field(default=5.0, ge=1, le=10)
    supporting_evidence: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)


class StrategicIntuitionSchema(BaseModel):
    organization_name: str = Field(..., min_length=1)
    decision_context: str = Field(...)
    insights: List[IntuitionInsightSchema]

# =============================================================================
# ENDPOINTS — Root & Health
# =============================================================================


@strategic_thinking_app.get("/")
def root():
    return {
        "service": "Strategic Thinking Tools Microservice",
        "version": "1.0.0",
        "techniques": [
            "First_Principles_Thinking", "Systems_Thinking", "Mental_Models",
            "Scenario_Planning", "Design_Thinking", "Reverse_Engineering",
            "Strategic_Foresight", "Analogical_Reasoning",
            "Strategic_Agility", "Strategic_Intuition",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@strategic_thinking_app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "module": "strategic-thinking",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "techniques_ready": [
            "first_principles", "systems_thinking", "mental_models",
            "scenario_planning", "design_thinking", "reverse_engineering",
            "strategic_foresight", "analogical_reasoning",
            "strategic_agility", "strategic_intuition",
        ],
    }

# =============================================================================
# ENDPOINTS — First Principles Thinking
# =============================================================================


@strategic_thinking_app.post("/first-principles/analyze")
def first_principles_analyze(data: FirstPrinciplesSchema):
    try:
        avg_confidence = sum(p.confidence for p in data.principles) / len(data.principles) if data.principles else 0
        total_assumptions = sum(len(p.assumptions_challenged) for p in data.principles)
        total_evidence = sum(len(p.evidence) for p in data.principles)
        return {
            "success": True,
            "organization": data.organization_name,
            "problem": data.problem_statement,
            "principles_count": len(data.principles),
            "average_confidence": round(avg_confidence, 2),
            "assumptions_challenged": total_assumptions,
            "evidence_items": total_evidence,
            "analysis_strength": "STRONG" if avg_confidence >= 7 and total_evidence >= len(data.principles) else "MODERATE",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Systems Thinking
# =============================================================================


@strategic_thinking_app.post("/systems/analyze")
def systems_thinking_analyze(data: SystemsThinkingSchema):
    try:
        feedback_loops = [e for e in data.elements if e.feedback_type != "NONE"]
        positive_loops = [e for e in data.elements if e.feedback_type == "POSITIVE"]
        negative_loops = [e for e in data.elements if e.feedback_type == "NEGATIVE"]
        stocks = [e for e in data.elements if e.element_type == "STOCK"]
        flows = [e for e in data.elements if e.element_type == "FLOW"]
        total_connections = sum(len(e.connections) for e in data.elements)
        complexity = "HIGH" if len(data.elements) > 10 or total_connections > 20 else \
                     "MODERATE" if len(data.elements) > 5 else "LOW"
        return {
            "success": True,
            "organization": data.organization_name,
            "system_name": data.system_name,
            "elements_count": len(data.elements),
            "stocks": len(stocks),
            "flows": len(flows),
            "feedback_loops": len(feedback_loops),
            "positive_loops": len(positive_loops),
            "negative_loops": len(negative_loops),
            "total_connections": total_connections,
            "complexity": complexity,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Mental Models
# =============================================================================


@strategic_thinking_app.post("/mental-models/analyze")
def mental_models_analyze(data: MentalModelsSchema):
    try:
        by_type = {}
        avg_confidence = 0
        for m in data.models:
            by_type.setdefault(m.model_type, []).append(m.model_name)
            avg_confidence += m.confidence
        avg_confidence = avg_confidence / len(data.models) if data.models else 0
        return {
            "success": True,
            "organization": data.organization_name,
            "decision_context": data.decision_context,
            "models_count": len(data.models),
            "models_by_type": {k: len(v) for k, v in by_type.items()},
            "average_confidence": round(avg_confidence, 2),
            "diversity_score": len(by_type) / 4 * 10,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Design Thinking
# =============================================================================


@strategic_thinking_app.post("/design-thinking/analyze")
def design_thinking_analyze(data: DesignThinkingSchema):
    try:
        phase_results = []
        overall_completion = 0
        for phase in data.phases:
            overall_completion += phase.completion_pct
            phase_results.append({
                "phase": phase.phase_name,
                "activities": len(phase.activities),
                "findings": len(phase.findings),
                "completion_pct": phase.completion_pct,
            })
        avg_completion = overall_completion / len(data.phases) if data.phases else 0
        completed_phases = sum(1 for p in data.phases if p.completion_pct >= 80)
        return {
            "success": True,
            "organization": data.organization_name,
            "challenge": data.challenge,
            "phases_count": len(data.phases),
            "average_completion": round(avg_completion, 1),
            "completed_phases": completed_phases,
            "results": phase_results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategic Foresight
# =============================================================================


@strategic_thinking_app.post("/foresight/analyze")
def strategic_foresight_analyze(data: StrategicForesightSchema):
    try:
        by_type = {}
        near_term = []
        long_term = []
        for signal in data.signals:
            by_type.setdefault(signal.signal_type, []).append(signal.signal_name)
            if signal.timeframe_years <= data.horizon_years // 2:
                near_term.append(signal.signal_name)
            else:
                long_term.append(signal.signal_name)
        avg_strength = sum(s.strength for s in data.signals) / len(data.signals) if data.signals else 0
        return {
            "success": True,
            "organization": data.organization_name,
            "horizon_years": data.horizon_years,
            "signals_count": len(data.signals),
            "signals_by_type": {k: len(v) for k, v in by_type.items()},
            "near_term_signals": near_term,
            "long_term_signals": long_term,
            "average_signal_strength": round(avg_strength, 2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Analogical Reasoning
# =============================================================================


@strategic_thinking_app.post("/analogical/analyze")
def analogical_reasoning_analyze(data: AnalogicalReasoningSchema):
    try:
        results = []
        for a in data.analogies:
            relevance = a.similarity_score * (1 - len(a.limitations) * 0.1)
            results.append({
                "source": a.source_domain,
                "target": a.target_domain,
                "similarity": a.similarity_score,
                "insights_count": len(a.key_insights),
                "limitations_count": len(a.limitations),
                "relevance_score": round(relevance, 2),
            })
        avg_similarity = sum(a.similarity_score for a in data.analogies) / len(data.analogies) if data.analogies else 0
        return {
            "success": True,
            "organization": data.organization_name,
            "problem_context": data.problem_context,
            "analogies_count": len(data.analogies),
            "average_similarity": round(avg_similarity, 2),
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategic Agility
# =============================================================================


@strategic_thinking_app.post("/agility/assess")
def strategic_agility_assess(data: StrategicAgilitySchema):
    try:
        gaps = []
        weighted_score = 0
        total_weight = 0
        for d in data.dimensions:
            gap = d.target_score - d.current_score
            gaps.append({
                "dimension": d.dimension_name,
                "current": d.current_score,
                "target": d.target_score,
                "gap": round(gap, 2),
            })
            weighted_score += d.current_score * d.weight
            total_weight += d.weight
        overall = weighted_score / total_weight if total_weight > 0 else 0
        maturity = "HIGHLY_AGILE" if overall >= 8 else "MODERATELY_AGILE" if overall >= 5 else "RIGID"
        return {
            "success": True,
            "organization": data.organization_name,
            "overall_agility_score": round(overall, 2),
            "maturity": maturity,
            "response_time_target_days": data.response_time_target_days,
            "gaps": gaps,
            "dimensions_count": len(data.dimensions),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =============================================================================
# ENDPOINTS — Strategic Intuition
# =============================================================================


@strategic_thinking_app.post("/intuition/evaluate")
def strategic_intuition_evaluate(data: StrategicIntuitionSchema):
    try:
        avg_confidence = sum(i.confidence for i in data.insights) / len(data.insights) if data.insights else 0
        by_source = {}
        total_risks = 0
        for insight in data.insights:
            by_source.setdefault(insight.source, []).append(insight.insight_name)
            total_risks += len(insight.risks)
        well_supported = sum(1 for i in data.insights if len(i.supporting_evidence) >= 2)
        return {
            "success": True,
            "organization": data.organization_name,
            "decision_context": data.decision_context,
            "insights_count": len(data.insights),
            "average_confidence": round(avg_confidence, 2),
            "well_supported_count": well_supported,
            "insights_by_source": {k: len(v) for k, v in by_source.items()},
            "total_risks_identified": total_risks,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# MOUNT HELPER
# =============================================================================

def mount(parent_app, prefix="/api/v1/strategic-thinking"):
    parent_app.mount(prefix, strategic_thinking_app)
