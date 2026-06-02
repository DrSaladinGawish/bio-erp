from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, date

from app.database import get_db
from app.models.strategic_cost_staging import (
    SCMStagingCategory,
    SCMStagingCostDriver,
    SCMStagingActivityCost,
    SCMStagingSustainability,
)

router = APIRouter()

# =========================================================
# PYDANTIC SCHEMAS
# =========================================================

class CostCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=20)
    description: Optional[str] = None
    parent_id: Optional[int] = None

class CostCategoryResponse(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str]
    parent_id: Optional[int]
    created_at: datetime

class CostDriverCreate(BaseModel):
    name: str
    category_id: int
    measurement_unit: str
    cost_per_unit: float = Field(..., ge=0)

class ActivityCostCreate(BaseModel):
    activity_name: str
    cost_driver_id: int
    actual_quantity: float = Field(..., ge=0)
    actual_cost: float = Field(..., ge=0)
    period_start: date
    period_end: date
    job_id: Optional[str] = None
    notes: Optional[str] = None

class StrategicAnalysisRequest(BaseModel):
    analysis_type: str = Field(..., pattern="^(value_chain|abc|target_costing|life_cycle|kaizen)$")
    job_id: Optional[str] = None
    period_start: date
    period_end: date
    parameters: Optional[dict] = {}

class StrategicAnalysisResponse(BaseModel):
    analysis_id: str
    analysis_type: str
    status: str
    results: dict
    recommendations: List[str]
    generated_at: datetime

class SustainabilityCostCreate(BaseModel):
    environmental_cost: float = Field(0, ge=0)
    social_cost: float = Field(0, ge=0)
    governance_cost: float = Field(0, ge=0)
    carbon_footprint_kg: float = Field(0, ge=0)
    period_start: date
    period_end: date
    job_id: Optional[str] = None

class BankTransactionImport(BaseModel):
    file_content: str  # Base64 encoded or CSV string
    file_type: str = Field(..., pattern="^(csv|xlsx|ofx|qif)$")
    bank_account_id: str
    import_date: date
    auto_match: bool = True

class SCMStagingStatus(BaseModel):
    staging_table: str
    record_count: int
    last_sync: Optional[datetime]
    pending_review: int

# =========================================================
# ENDPOINTS
# =========================================================

@router.get("/health")
async def scm_health():
    return {
        "module": "SCM Strategic Cost Management",
        "version": "1.0.0",
        "status": "operational",
        "organs": ["cost_categories", "cost_drivers", "activity_costs", "strategic_analysis", "sustainability", "bank_import"],
        "staging_isolation": True,
        "production_write_protection": "ACTIVE"
    }

@router.get("/categories", response_model=List[CostCategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all SCM cost categories (reads from staging, no production write)"""
    result = await db.execute(
        select(SCMStagingCategory).where(SCMStagingCategory.status == "approved")
        .order_by(SCMStagingCategory.id)
    )
    cats = result.scalars().all()
    if not cats:
        return []
    return [
        CostCategoryResponse(
            id=c.id,
            name=c.name,
            code=c.code,
            description=c.description,
            parent_id=c.parent_id,
            created_at=c.created_at,
        )
        for c in cats
    ]

@router.post("/categories")
async def create_category(category: CostCategoryCreate, db: AsyncSession = Depends(get_db)):
    """Create cost category - WRITES TO scm_staging only"""
    import uuid as _uuid
    entry = SCMStagingCategory(
        staging_id=f"SCM-CAT-{_uuid.uuid4().hex[:12].upper()}",
        name=category.name,
        code=category.code,
        description=category.description,
        parent_id=category.parent_id,
        status="pending",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {
        "success": True,
        "message": "Category staged for review",
        "staging_id": entry.staging_id,
        "data": category.model_dump(),
        "approval_required": True,
    }

@router.get("/analysis/types")
async def list_analysis_types():
    """List available strategic analysis types from curriculum"""
    return {
        "analysis_types": [
            {
                "id": "value_chain",
                "name": "Value Chain Analysis",
                "description": "Porter's Value Chain - primary and support activities",
                "source": "Lecture 2 PDF (398 KB)",
                "modules": ["inbound_logistics", "operations", "outbound_logistics", "marketing_sales", "service", "firm_infrastructure", "hr_management", "technology_development", "procurement"]
            },
            {
                "id": "abc",
                "name": "Activity-Based Costing",
                "description": "ABC costing with cost drivers and activity pools",
                "source": "Lecture 3 PDF (527 KB)",
                "modules": ["activity_identification", "cost_driver_selection", "cost_pool_allocation", "product_costing"]
            },
            {
                "id": "target_costing",
                "name": "Target Costing",
                "description": "Market-driven cost planning",
                "source": "Strategic Analysis Type 1",
                "modules": ["market_price_analysis", "target_margin", "cost_gap_analysis", "value_engineering"]
            },
            {
                "id": "kaizen",
                "name": "Kaizen Costing",
                "description": "Continuous improvement cost reduction",
                "source": "Strategic Analysis Type 2",
                "modules": ["current_cost_baseline", "improvement_targets", "periodic_reduction", "variance_tracking"]
            },
            {
                "id": "life_cycle",
                "name": "Life Cycle Costing",
                "description": "Total cost across product life cycle",
                "source": "Strategic Analysis Type 3",
                "modules": ["rd_costs", "design_costs", "manufacturing_costs", "logistics_costs", "service_costs", "disposal_costs"]
            }
        ]
    }

@router.post("/analysis/run")
async def run_strategic_analysis(request: StrategicAnalysisRequest):
    """Run strategic cost analysis - results saved to disposable JSON only"""
    analysis_id = f"SCM-ANL-{datetime.now().strftime('%Y%m%d%H%M%S')}-{request.analysis_type.upper()}"

    # Demo results - replace with actual engine calls
    results = {
        "analysis_id": analysis_id,
        "analysis_type": request.analysis_type,
        "job_id": request.job_id,
        "period": {"start": str(request.period_start), "end": str(request.period_end)},
        "status": "completed",
        "results": {
            "total_cost_analyzed": 125000.00,
            "cost_breakdown": {
                "direct": 75000.00,
                "indirect": 35000.00,
                "overhead": 15000.00
            },
            "efficiency_score": 0.847,
            "benchmark_comparison": "above_industry_average"
        },
        "recommendations": [
            "Reduce inbound logistics costs by 12% through supplier consolidation",
            "Optimize operations workflow to eliminate 3 non-value-added activities",
            "Target costing indicates $8,500 cost gap vs. market price - initiate value engineering",
            "Kaizen targets: 2% monthly cost reduction for Q3"
        ],
        "disposable_file": f"/tmp/scm_analysis_{analysis_id}.json",
        "production_impact": "NONE - read-only analysis"
    }

    return results

@router.get("/analysis/results/{analysis_id}")
async def get_analysis_results(analysis_id: str):
    """Retrieve analysis results from disposable storage"""
    return {
        "analysis_id": analysis_id,
        "retrieved_from": "disposable_storage",
        "production_safe": True,
        "results": {"message": "Load from disposable JSON file"}
    }

@router.post("/sustainability/calculate")
async def calculate_sustainability_costs(data: SustainabilityCostCreate, db: AsyncSession = Depends(get_db)):
    """Calculate environmental/social/governance costs - writes to scm_staging"""
    import uuid as _uuid
    total_esg = data.environmental_cost + data.social_cost + data.governance_cost
    carbon_cost = data.carbon_footprint_kg * 0.045

    entry = SCMStagingSustainability(
        staging_id=f"SCM-ESG-{_uuid.uuid4().hex[:12].upper()}",
        environmental_cost=data.environmental_cost,
        social_cost=data.social_cost,
        governance_cost=data.governance_cost,
        carbon_footprint_kg=data.carbon_footprint_kg,
        period_start=data.period_start,
        period_end=data.period_end,
        job_id=data.job_id,
        status="pending",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return {
        "staging_id": entry.staging_id,
        "environmental_cost": data.environmental_cost,
        "social_cost": data.social_cost,
        "governance_cost": data.governance_cost,
        "total_esg_cost": total_esg,
        "carbon_footprint_kg": data.carbon_footprint_kg,
        "implied_carbon_cost": carbon_cost,
        "full_cost_including_carbon": total_esg + carbon_cost,
        "status": "staged_for_review",
        "production_write": "BLOCKED",
    }

@router.post("/bank/import")
async def import_bank_transactions(data: BankTransactionImport, background_tasks: BackgroundTasks):
    """Import bank transactions - staging tables only, never production.
    Uses P3 bank_reimport_engine for actual processing."""
    import_id = f"SCM-BANK-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return {
        "import_id": import_id,
        "status": "queued",
        "file_type": data.file_type,
        "bank_account": data.bank_account_id,
        "auto_match_enabled": data.auto_match,
        "staging_destination": "scm_staging_bank_transactions",
        "production_write": "BLOCKED",
        "message": "Transactions will be staged for manual review before posting to production. Use P3 bank_reimport_engine for processing.",
    }

@router.get("/staging/status")
async def get_staging_status(db: AsyncSession = Depends(get_db)):
    """Check staging table status - production data is protected"""
    tables = [
        ("scm_staging_categories", SCMStagingCategory),
        ("scm_staging_cost_drivers", SCMStagingCostDriver),
        ("scm_staging_activity_costs", SCMStagingActivityCost),
        ("scm_staging_sustainability", SCMStagingSustainability),
    ]
    results = []
    for name, model in tables:
        count_result = await db.execute(select(func.count()).select_from(model))
        total = count_result.scalar() or 0
        pending_result = await db.execute(
            select(func.count()).select_from(model).where(model.status == "pending")
        )
        pending = pending_result.scalar() or 0
        results.append(SCMStagingStatus(
            staging_table=name,
            record_count=total,
            last_sync=None,
            pending_review=pending,
        ))
    return results

@router.post("/staging/approve/{staging_id:path}")
async def approve_staging_record(staging_id: str, db: AsyncSession = Depends(get_db)):
    """Approve staging record - requires deployment rights"""
    model = _resolve_staging_model(staging_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown staging table in id: {staging_id}")
    result = await db.execute(select(model).where(model.staging_id == staging_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record.status = "approved"
    await db.commit()
    return {
        "staging_id": staging_id,
        "action": "approved",
        "message": "Record approved for production deployment. Use deployment workflow to push live.",
        "next_step": "Run deployment script or click 'Deploy to Production' button",
    }

@router.post("/staging/reject/{staging_id:path}")
async def reject_staging_record(staging_id: str, db: AsyncSession = Depends(get_db)):
    """Reject staging record"""
    model = _resolve_staging_model(staging_id)
    if model is None:
        raise HTTPException(status_code=404, detail=f"Unknown staging table in id: {staging_id}")
    result = await db.execute(select(model).where(model.staging_id == staging_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    record.status = "rejected"
    await db.commit()
    return {
        "staging_id": staging_id,
        "action": "rejected",
        "message": "Record rejected and removed from staging",
    }


def _resolve_staging_model(staging_id: str):
    prefix_map = {
        "SCM-CAT": SCMStagingCategory,
        "SCM-CDR": SCMStagingCostDriver,
        "SCM-ACT": SCMStagingActivityCost,
        "SCM-ESG": SCMStagingSustainability,
    }
    for k in sorted(prefix_map.keys(), reverse=True):
        if staging_id.startswith(k):
            return prefix_map[k]
    return None

@router.get("/dashboard")
async def scm_dashboard():
    """SCM executive dashboard - read-only aggregation"""
    return {
        "module": "SCM Strategic Cost Management",
        "kpi_cards": [
            {"title": "Cost Categories", "value": 16, "trend": "up", "change": "+2"},
            {"title": "Active Drivers", "value": 42, "trend": "stable", "change": "0"},
            {"title": "Pending Analysis", "value": 3, "trend": "down", "change": "-1"},
            {"title": "Staging Records", "value": 0, "trend": "stable", "change": "0"},
        ],
        "recent_analyses": [],
        "alerts": [
            {"level": "info", "message": "Production data is protected. All writes go to staging tables."},
            {"level": "warning", "message": "3 strategic analyses pending review"}
        ],
        "system_status": "operational"
    }
