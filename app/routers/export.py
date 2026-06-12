import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ihe_models import (
    PNRMaster,
    Client,
    Vendor,
    Employee,
    Bank,
    ChartOfAccounts,
    BankTransaction,
    SalesInvoice,
    PurchaseVoucher,
    JournalVoucher,
)

router = APIRouter(prefix="/api/v1/export", tags=["Export"])

ENTITY_MAP = {
    "pnrs": PNRMaster,
    "clients": Client,
    "vendors": Vendor,
    "employees": Employee,
    "banks": Bank,
    "accounts": ChartOfAccounts,
    "transactions": BankTransaction,
    "invoices": SalesInvoice,
    "vouchers": PurchaseVoucher,
    "journal-vouchers": JournalVoucher,
}


@router.get("/{entity}")
async def export_entity(entity: str, db: AsyncSession = Depends(get_db)):
    model = ENTITY_MAP.get(entity)
    if not model:
        raise HTTPException(status_code=404, detail=f"Unknown entity: {entity}")

    result = await db.execute(select(model))
    rows = result.scalars().all()
    if not rows:
        return {"entity": entity, "rows": 0, "message": "No data"}

    columns = [c.name for c in model.__table__.columns]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([getattr(row, col, "") for col in columns])

    output.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={entity}_{ts}.csv"},
    )
