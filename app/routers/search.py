from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models.ihe_models import PNRMaster, Client, Vendor

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


class SearchResult(BaseModel):
    pnrs: int = 0
    clients: int = 0
    vendors: int = 0


@router.get("", response_model=SearchResult)
async def search(
    q: str = Query("", description="Search query"), db: AsyncSession = Depends(get_db)
):
    results = SearchResult()
    if not q:
        try:
            r1 = await db.execute(select(func.count()).select_from(PNRMaster))
            results.pnrs = r1.scalar() or 0
        except Exception:
            pass
        try:
            r2 = await db.execute(select(func.count()).select_from(Client))
            results.clients = r2.scalar() or 0
        except Exception:
            pass
        try:
            r3 = await db.execute(select(func.count()).select_from(Vendor))
            results.vendors = r3.scalar() or 0
        except Exception:
            pass
    return results
