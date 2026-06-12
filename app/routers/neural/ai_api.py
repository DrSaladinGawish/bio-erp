from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, RequirePermission
from app.models.auth import User
from app.models.neural.prediction import (
    NeuralPrediction,
    NeuralFeatureStore,
    NeuralTrainingHistory,
    NeuralMemory,
)
from app.schemas.neural.nodes import (
    PredictionCreate,
    PredictionResponse,
    PredictionRequest,
    HumanFeedback,
    FeatureStoreCreate,
    FeatureStoreResponse,
    TrainingCreate,
    TrainingResponse,
    MemoryCreate,
    MemoryResponse,
    DashboardInsight,
)
from app.services.neural.predictor import PredictorService

router = APIRouter(prefix="/api/v1/neural", tags=["Neural AI"])


@router.post("/predict", response_model=dict)
async def create_prediction(
    req: PredictionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.predict")),
):
    result = await PredictorService.predict(db, req.prediction_type, req.entity_id, req.context)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"])
    return result


@router.post("/predictions", response_model=PredictionResponse, status_code=status.HTTP_201_CREATED)
async def create_prediction_record(
    req: PredictionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.create")),
):
    prediction = NeuralPrediction(**req.model_dump())
    db.add(prediction)
    await db.commit()
    await db.refresh(prediction)
    return prediction


@router.get("/predictions", response_model=dict)
async def list_predictions(
    prediction_type: str | None = Query(None, description="Filter by prediction type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.read")),
):
    return await PredictorService.list_predictions(db, prediction_type, page, page_size)


@router.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.read")),
):
    result = await db.execute(select(NeuralPrediction).where(NeuralPrediction.id == prediction_id))
    prediction = result.scalar_one_or_none()
    if not prediction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return prediction


@router.post("/predictions/{prediction_id}/feedback", response_model=dict)
async def submit_feedback(
    prediction_id: int,
    feedback: HumanFeedback,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.feedback")),
):
    result = await PredictorService.submit_feedback(db, prediction_id, feedback.actual_value)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.post("/features", response_model=FeatureStoreResponse, status_code=status.HTTP_201_CREATED)
async def create_feature(
    req: FeatureStoreCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.create")),
):
    feature = NeuralFeatureStore(**req.model_dump())
    db.add(feature)
    await db.commit()
    await db.refresh(feature)
    return feature


@router.get("/features", response_model=list[FeatureStoreResponse])
async def list_features(
    feature_group: str | None = Query(None),
    feature_key: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.read")),
):
    query = select(NeuralFeatureStore).where(NeuralFeatureStore.is_active.is_(True))
    if feature_group:
        query = query.where(NeuralFeatureStore.feature_group == feature_group)
    if feature_key:
        query = query.where(NeuralFeatureStore.feature_key == feature_key)
    query = query.order_by(NeuralFeatureStore.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/training", response_model=TrainingResponse, status_code=status.HTTP_201_CREATED)
async def create_training(
    req: TrainingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.train")),
):
    training = NeuralTrainingHistory(**req.model_dump(), training_status="pending")
    db.add(training)
    await db.commit()
    await db.refresh(training)
    return training


@router.get("/training", response_model=list[TrainingResponse])
async def list_training(
    model_name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.read")),
):
    query = select(NeuralTrainingHistory).order_by(NeuralTrainingHistory.created_at.desc())
    if model_name:
        query = query.where(NeuralTrainingHistory.model_name == model_name)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/memory", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(
    req: MemoryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.create")),
):
    memory = NeuralMemory(**req.model_dump())
    db.add(memory)
    await db.commit()
    await db.refresh(memory)
    return memory


@router.get("/memory", response_model=list[MemoryResponse])
async def list_memory(
    memory_type: str | None = Query(None),
    memory_key: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.read")),
):
    query = select(NeuralMemory).where(NeuralMemory.is_active.is_(True))
    if memory_type:
        query = query.where(NeuralMemory.memory_type == memory_type)
    if memory_key:
        query = query.where(NeuralMemory.memory_key == memory_key)
    query = query.order_by(NeuralMemory.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.delete")),
):
    result = await db.execute(select(NeuralMemory).where(NeuralMemory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    memory.is_active = False
    await db.commit()


@router.get("/dashboard", response_model=dict)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("neural.read")),
):
    return await PredictorService.get_dashboard(db)
