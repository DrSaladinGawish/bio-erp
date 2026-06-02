"""EventCore Bridge — enables BIO_ERP to sync with EventCore ERP (Port 8001)."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/api/v1/eventcore-bridge", tags=["EventCore Bridge"])

EVENTCORE_URL = getattr(settings, "eventcore_base_url", "http://localhost:8001")


@router.get("/status")
async def bridge_status():
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{EVENTCORE_URL}/api/v1/health")
            ec_status = resp.json()
        return {
            "eventcore_reachable": True,
            "eventcore_url": EVENTCORE_URL,
            "eventcore_status": ec_status,
        }
    except Exception as e:
        return {
            "eventcore_reachable": False,
            "eventcore_url": EVENTCORE_URL,
            "error": str(e),
        }


@router.get("/vendors")
async def get_vendors_for_eventcore(db: AsyncSession = Depends(get_db)):
    """Expose vendors to EventCore for sync."""
    from app.models.supplier import Supplier
    from sqlalchemy import select
    result = await db.execute(select(Supplier).where(Supplier.is_active == True))
    vendors = result.scalars().all()
    return [
        {
            "id": v.id,
            "name": v.name_en,
            "email": v.email,
            "phone": v.phone,
            "vat_number": v.tax_id,
            "bank_account": v.bank_account,
            "category": v.service_category,
        }
        for v in vendors
    ]


@router.get("/gl-accounts")
async def get_gl_accounts_for_eventcore(db: AsyncSession = Depends(get_db)):
    """Expose GL accounts to EventCore for reference."""
    from app.models.coa import Account
    from sqlalchemy import select
    result = await db.execute(select(Account).where(Account.is_active == True))
    accounts = result.scalars().all()
    return [
        {
            "id": a.id,
            "code": a.code,
            "name_en": a.name_en,
            "type": a.account_type,
            "balance": float(a.balance) if a.balance else 0,
        }
        for a in accounts
    ]


@router.post("/journal-entries")
async def receive_journal_entry(data: dict, db: AsyncSession = Depends(get_db)):
    """Receive a journal entry from EventCore."""
    from app.models.transaction import Transaction
    from datetime import datetime, timezone
    entry = Transaction(
        reference=data.get("reference", f"EC-{uuid.uuid4().hex[:8].upper()}"),
        description=data.get("description", "Journal from EventCore"),
        debit=data.get("debit", 0),
        credit=data.get("credit", 0),
        account_code=data.get("account_code"),
        transaction_date=datetime.now(timezone.utc),
        source_system="eventcore",
        status="posted",
    )
    db.add(entry)
    await db.flush()
    return {"status": "received", "id": entry.id, "reference": entry.reference}


@router.post("/sync/events")
async def receive_event(data: dict, db: AsyncSession = Depends(get_db)):
    """Receive an event sync from EventCore."""
    from app.services.event_bridge import EventBridge
    event = await EventBridge.sync_web_to_local(db, data)
    return {"status": "synced", "event_id": event.event_id}
