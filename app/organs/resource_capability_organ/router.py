"""
Resource & Capability Analysis Organ — FastAPI Async Router
BIO-ERP v5.3.0 — resource_capability_organ
"""

from datetime import datetime

from fastapi import APIRouter

from app.organs.resource_capability_organ.schemas import (
    CapabilityMappingSchema,
    CoreCompetencyAnalysisSchema,
    DynamicCapabilitiesSchema,
    KnowledgeAssetsSchema,
    OutsourcingAnalysisSchema,
    ResourceAuditSchema,
    ValueChainAnalysisSchema,
    VRIOAnalysisSchema,
)
from app.organs.resource_capability_organ.services import (
    CapabilityMappingEngine,
    CoreCompetencyEngine,
    DynamicCapabilitiesEngine,
    KnowledgeAssetsEngine,
    OutsourcingEngine,
    ResourceAuditEngine,
    ValueChainEngine,
    VRIOEngine,
)

router = APIRouter()


def _envelope(technique: str, payload: dict) -> dict:
    return {
        "success": True,
        "technique": technique,
        "result": payload.get("result", {}),
        "interpretation": payload.get("interpretation", {}),
        "timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# ROOT & HEALTH
# =============================================================================


@router.get("/")
async def root():
    return {
        "service": "Resource & Capability Analysis Organ",
        "version": "5.3.0",
        "techniques_count": 8,
        "techniques": [
            "vrio-framework",
            "value-chain-analysis",
            "core-competency-assessment",
            "dynamic-capabilities",
            "resource-audit",
            "capability-mapping",
            "knowledge-assets-assessment",
            "outsourcing-analysis",
        ],
        "docs": "/docs",
        "health": "/health",
    }


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "module": "resource-capability",
        "version": "5.3.0",
        "timestamp": datetime.now().isoformat(),
        "engines_ready": [
            "vrio",
            "value_chain",
            "core_competency",
            "dynamic_capabilities",
            "resource_audit",
            "capability_mapping",
            "knowledge_assets",
            "outsourcing",
        ],
    }


# =============================================================================
# 1. VRIO FRAMEWORK
# =============================================================================


@router.post("/vrio/analyze")
async def vrio_analyze(req: VRIOAnalysisSchema):
    return {
        "organization": req.organization,
        **_envelope(
            "VRIO_FRAMEWORK",
            VRIOEngine.analyze([r.model_dump() for r in req.resources]),
        ),
    }


# =============================================================================
# 2. VALUE CHAIN ANALYSIS
# =============================================================================


@router.post("/value-chain/analyze")
async def value_chain_analyze(req: ValueChainAnalysisSchema):
    return {
        "organization": req.organization,
        **_envelope(
            "VALUE_CHAIN_ANALYSIS",
            ValueChainEngine.analyze(
                req.primary_activities.model_dump(), req.support_activities.model_dump()
            ),
        ),
    }


# =============================================================================
# 3. CORE COMPETENCY ASSESSMENT
# =============================================================================


@router.post("/core-competency/analyze")
async def core_competency_analyze(req: CoreCompetencyAnalysisSchema):
    return {
        "organization": req.organization,
        **_envelope(
            "CORE_COMPETENCY_ASSESSMENT",
            CoreCompetencyEngine.analyze(
                [c.model_dump() for c in req.competencies],
                req.building_horizon_quarters,
            ),
        ),
    }


# =============================================================================
# 4. DYNAMIC CAPABILITIES
# =============================================================================


@router.post("/dynamic-capabilities/analyze")
async def dynamic_capabilities_analyze(req: DynamicCapabilitiesSchema):
    return {
        "organization": req.organization,
        **_envelope(
            "DYNAMIC_CAPABILITIES",
            DynamicCapabilitiesEngine.analyze(
                req.sensing_capabilities.model_dump(),
                req.seizing_capabilities.model_dump(),
                req.reconfiguring_capabilities.model_dump(),
            ),
        ),
    }


# =============================================================================
# 5. RESOURCE AUDIT
# =============================================================================


@router.post("/resource-audit/analyze")
async def resource_audit_analyze(req: ResourceAuditSchema):
    return {
        "organization": req.organization,
        **_envelope(
            "RESOURCE_AUDIT",
            ResourceAuditEngine.analyze(
                [t.model_dump() for t in req.tangible_resources],
                [i.model_dump() for i in req.intangible_resources],
                [h.model_dump() for h in req.human_resources],
            ),
        ),
    }


# =============================================================================
# 6. CAPABILITY MAPPING
# =============================================================================


@router.post("/capability-mapping/analyze")
async def capability_mapping_analyze(req: CapabilityMappingSchema):
    return {
        "organization": req.organization,
        **_envelope(
            "CAPABILITY_MAPPING",
            CapabilityMappingEngine.analyze([c.model_dump() for c in req.capabilities]),
        ),
    }


# =============================================================================
# 7. KNOWLEDGE ASSETS ASSESSMENT
# =============================================================================


@router.post("/knowledge-assets/analyze")
async def knowledge_assets_analyze(req: KnowledgeAssetsSchema):
    return {
        "organization": req.organization,
        **_envelope(
            "KNOWLEDGE_ASSETS_ASSESSMENT",
            KnowledgeAssetsEngine.analyze(
                req.human_capital.model_dump(),
                req.structural_capital.model_dump(),
                req.relational_capital.model_dump(),
            ),
        ),
    }


# =============================================================================
# 8. OUTSOURCING ANALYSIS
# =============================================================================


@router.post("/outsourcing/analyze")
async def outsourcing_analyze(req: OutsourcingAnalysisSchema):
    return {
        "organization": req.organization,
        **_envelope(
            "OUTSOURCING_ANALYSIS",
            OutsourcingEngine.analyze(
                [a.model_dump() for a in req.activities], req.contract_years
            ),
        ),
    }
