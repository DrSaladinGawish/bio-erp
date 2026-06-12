from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..e_invoice_service import generate_bulk_xml, generate_invoice_xml
from ..models_production import SalesInvoice

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/einvoice", tags=["E-Invoice XML"])


@router.get("/invoices")
async def list_invoices(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(SalesInvoice.id, SalesInvoice.invoice_no, SalesInvoice.invoice_date, SalesInvoice.total, SalesInvoice.status)
    filters = []
    if date_from:
        filters.append(SalesInvoice.invoice_date >= date_from)
    if date_to:
        filters.append(SalesInvoice.invoice_date <= date_to)
    if filters:
        stmt = stmt.where(*filters)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(SalesInvoice.invoice_date.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).all()
    return {
        "data": [{"id": r.id, "invoice_no": r.invoice_no, "invoice_date": r.invoice_date.isoformat() if r.invoice_date else "", "total": float(r.total or 0), "status": r.status} for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/generate/{invoice_id}")
async def generate_xml(
    invoice_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    result = await generate_invoice_xml(session, invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/generate/{invoice_id}/download")
async def download_xml(
    invoice_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    result = await generate_invoice_xml(session, invoice_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return PlainTextResponse(
        result["xml"],
        media_type="application/xml",
        headers={"Content-Disposition": f"attachment; filename=einvoice_{invoice_id}.xml"},
    )


@router.get("/generate-bulk")
async def generate_bulk(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    date_from: Annotated[Optional[date], Query()] = None,
    date_to: Annotated[Optional[date], Query()] = None,
):
    results = await generate_bulk_xml(session, date_from, date_to)
    return {"invoices": results, "count": len(results)}
