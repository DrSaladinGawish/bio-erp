"""
BI Router — Business Intelligence / Neural
Prefix: /api/v1/bi
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from ..models_empty_modules import NeuralPrediction

router = APIRouter(prefix="/api/v1/bi", tags=["Business Intelligence"])

@router.get("/predictions")
async def list_predictions(session: AsyncSession = Depends(get_async_session)):
    rows = (await session.execute(select(NeuralPrediction).order_by(NeuralPrediction.created_at.desc()))).scalars().all()
    return {"data": [{"id": r.id, "model_name": r.model_name, "prediction_type": r.prediction_type, "predicted_value": r.predicted_value, "confidence": r.confidence} for r in rows], "total": len(rows)}

@router.get("/summary")
async def bi_summary(session: AsyncSession = Depends(get_async_session)):
    total = (await session.execute(select(func.count(NeuralPrediction.id)))).scalar() or 0
    models = (await session.execute(select(NeuralPrediction.model_name.distinct()))).scalars().all()
    return {"total_predictions": total, "active_models": list(models)}
