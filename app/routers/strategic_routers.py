from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.schemas.strategic_schemas import (
    TargetCostingCreate,
    TargetCostingResponse,
    LifeCycleCostCreate,
    LifeCycleCostResponse,
    ActivityCostPoolCreate,
    ActivityCostPoolResponse,
    ValueChainCreate,
    ValueChainResponse,
    KaizenCreate,
    KaizenResponse,
    CostVarianceCreate,
    CostVarianceResponse,
    BSCCreate,
    BSCResponse,
    BSCObjectiveCreate,
    BSCObjectiveResponse,
    BSCIndicatorCreate,
    BSCIndicatorResponse,
    BSCMeasurementCreate,
    BSCMeasurementResponse,
    EventProfitabilityResponse,
)
from app.services.strategic_services import (
    StrategicCostService,
    BalancedScorecardService,
    EventProfitabilityService,
)

router = APIRouter(prefix="/strategic", tags=["Strategic Cost Management"])


# === TARGET COSTING ===


@router.post("/target-costing", response_model=TargetCostingResponse, status_code=201)
async def create_target_costing(
    data: TargetCostingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await StrategicCostService.create_target_costing(db, data.model_dump())


@router.get("/target-costing", response_model=list[TargetCostingResponse])
async def list_target_costing(
    event_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await StrategicCostService.list_target_costing(db, event_id)


# === LIFE CYCLE COSTING ===


@router.post("/lifecycle-cost", response_model=LifeCycleCostResponse, status_code=201)
async def create_lifecycle_cost(
    data: LifeCycleCostCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await StrategicCostService.create_lifecycle_cost(db, data.model_dump())


@router.get("/lifecycle-cost/{event_id}", response_model=list[LifeCycleCostResponse])
async def list_lifecycle_costs(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await StrategicCostService.list_lifecycle_costs(db, event_id)


# === ACTIVITY-BASED COSTING ===


@router.post("/abc/pool", response_model=ActivityCostPoolResponse, status_code=201)
async def create_abc_pool(
    data: ActivityCostPoolCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await StrategicCostService.create_abc_pool(db, data.model_dump())


@router.get("/abc/event/{event_id}/analysis")
async def get_abc_analysis(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await StrategicCostService.get_abc_event_analysis(db, event_id)


# === VALUE CHAIN ANALYSIS ===


@router.post("/value-chain", response_model=ValueChainResponse, status_code=201)
async def create_value_chain(
    data: ValueChainCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await StrategicCostService.create_value_chain(db, data.model_dump())


@router.get("/value-chain/event/{event_id}/analysis")
async def get_value_chain_analysis(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await StrategicCostService.get_value_chain_analysis(db, event_id)


# === KAIZEN COSTING ===


@router.post("/kaizen", response_model=KaizenResponse, status_code=201)
async def create_kaizen(
    data: KaizenCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await StrategicCostService.create_kaizen(db, data.model_dump())


@router.put("/kaizen/{kaizen_id}/result", response_model=KaizenResponse)
async def update_kaizen_result(
    kaizen_id: int,
    actual_cost: float = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.update")),
):
    record = await StrategicCostService.update_kaizen_result(db, kaizen_id, actual_cost)
    if not record:
        raise HTTPException(status_code=404, detail="Kaizen record not found")
    return record


@router.get("/kaizen", response_model=list[KaizenResponse])
async def list_kaizen(
    event_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await StrategicCostService.list_kaizen(db, event_id)


# === COST VARIANCE ANALYSIS ===


@router.post("/variance", response_model=CostVarianceResponse, status_code=201)
async def create_variance(
    data: CostVarianceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await StrategicCostService.create_variance(db, data.model_dump())


@router.get("/variance", response_model=list[CostVarianceResponse])
async def list_variances(
    event_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await StrategicCostService.list_variances(db, event_id)


# === BALANCED SCORECARD ===


@router.post("/bsc", response_model=BSCResponse, status_code=201)
async def create_bsc(
    data: BSCCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await BalancedScorecardService.create_bsc(db, data.model_dump())


@router.get("/bsc/{bsc_id}", response_model=BSCResponse)
async def get_bsc(
    bsc_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    record = await BalancedScorecardService.get_bsc(db, bsc_id)
    if not record:
        raise HTTPException(status_code=404, detail="BSC not found")
    return record


@router.get("/bsc", response_model=list[BSCResponse])
async def list_bsc(
    event_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await BalancedScorecardService.list_bsc(db, event_id)


@router.post("/bsc/objectives", response_model=BSCObjectiveResponse, status_code=201)
async def create_bsc_objective(
    data: BSCObjectiveCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await BalancedScorecardService.create_objective(db, data.model_dump())


@router.post("/bsc/indicators", response_model=BSCIndicatorResponse, status_code=201)
async def create_bsc_indicator(
    data: BSCIndicatorCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await BalancedScorecardService.create_indicator(db, data.model_dump())


@router.post(
    "/bsc/measurements", response_model=BSCMeasurementResponse, status_code=201
)
async def create_bsc_measurement(
    data: BSCMeasurementCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    return await BalancedScorecardService.create_measurement(db, data.model_dump())


@router.get("/bsc/event/{event_id}/dashboard")
async def get_bsc_dashboard(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    return await BalancedScorecardService.get_bsc_dashboard(db, event_id)


# === EVENT PROFITABILITY ===


@router.post(
    "/profitability/event/{event_id}", response_model=EventProfitabilityResponse
)
async def calculate_profitability(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.create")),
):
    record = await EventProfitabilityService.calculate_profitability(db, event_id)
    if not record:
        raise HTTPException(status_code=404, detail="Event not found")
    return record


@router.get(
    "/profitability/event/{event_id}", response_model=EventProfitabilityResponse
)
async def get_profitability(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("costing.read")),
):
    record = await EventProfitabilityService.get_profitability(db, event_id)
    if not record:
        raise HTTPException(
            status_code=404, detail="No profitability data. Run POST first."
        )
    return record
