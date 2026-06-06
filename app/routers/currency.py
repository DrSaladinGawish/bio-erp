from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.currency import Currency
from app.services.currency_sync import CurrencySyncService
from app.services.currency_service import currency_service
from app.services.audit_logger import AuditLogger

router = APIRouter(prefix="/api/v1/currencies", tags=["Currencies"])
conversion_router = APIRouter(prefix="/api/v1/currency", tags=["Currency Conversion"])


class CurrencyUpdate(BaseModel):
    mid_rate: float | None = None
    buy_rate: float | None = None
    sell_rate: float | None = None


@router.get("")
async def list_currencies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Currency).where(Currency.is_active))
    return result.scalars().all()


@router.post("/sync")
async def sync_currencies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("currency.sync")),
):
    service = CurrencySyncService(db)
    result = await service.sync_from_cbe()
    logger = AuditLogger(db)
    await logger.log(
        "SYNC",
        "Currency",
        description=f"CBE sync: {len(result['updated'])} updated, {len(result['failed'])} failed",
        actor_id=user.id,
    )
    return result


@router.post("/{currency_id}/rate")
async def update_rate(
    currency_id: int,
    req: CurrencyUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("currency.update")),
):
    result = await db.execute(select(Currency).where(Currency.id == currency_id))
    currency = result.scalar_one_or_none()
    if not currency:
        return {"error": "Currency not found"}
    if req.mid_rate is not None:
        currency.mid_rate = req.mid_rate
    if req.buy_rate is not None:
        currency.buy_rate = req.buy_rate
    if req.sell_rate is not None:
        currency.sell_rate = req.sell_rate
    logger = AuditLogger(db)
    await logger.log(
        "UPDATE", "Currency", currency_id, new_value=req.model_dump(), actor_id=user.id
    )
    return currency


@conversion_router.get("/convert")
async def convert_currency(
    amount: float = Query(..., gt=0, description="Amount to convert"),
    from_currency: str = Query(..., min_length=3, max_length=3, description="Source currency code (e.g. USD)"),
    to_currency: str = Query(..., min_length=3, max_length=3, description="Target currency code (e.g. EGP)"),
):
    result = await currency_service.convert(amount, from_currency, to_currency)
    return result


@conversion_router.get("/rates")
async def list_exchange_rates():
    if not currency_service.rates:
        await currency_service._refresh_rates()
    return {
        "base": "USD",
        "rates": currency_service.rates,
        "last_updated": currency_service.last_update.isoformat() if currency_service.last_update else None,
    }
