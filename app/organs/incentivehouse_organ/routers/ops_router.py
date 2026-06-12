from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ..database import get_async_session
from ..models_production import EventOperation

router = APIRouter(prefix="/api/v1/ops", tags=["Event Operations"])

@router.get("/operations")
async def list_operations(session: AsyncSession = Depends(get_async_session)):
    rows = (await session.execute(select(EventOperation).order_by(EventOperation.created_at.desc()))).scalars().all()
    return {"data": [{"id": r.id, "event_id": r.event_id, "ops_manager_id": r.ops_manager_id, "briefing_completed": r.briefing_completed, "sound_check_done": r.sound_check_done, "catering_final_count": r.catering_final_count, "lifecycle_status": getattr(r, "lifecycle_status", None), "created_at": str(r.created_at) if r.created_at else None} for r in rows], "total": len(rows)}

@router.get("/summary")
async def ops_summary(session: AsyncSession = Depends(get_async_session)):
    total = (await session.execute(select(func.count(EventOperation.id)))).scalar() or 0
    briefing = (await session.execute(select(func.count(EventOperation.id)).where(EventOperation.briefing_completed == True))).scalar() or 0
    return {"total_operations": total, "briefing_completed": briefing, "pending": total - briefing}
