"""
Bio-ERP Receiver for EventCore sync
Mount at: /api/v1/or/eventcore/...

Receives clean data pushed from EventCore (port 8001)
and persists into Bio-ERP PostgreSQL using existing models.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/eventcore", tags=["EventCore Ingest"])


class IngestResult(BaseModel):
    accepted: int
    rejected: int
    errors: List[str]


def verify_bridge_token(x_bridge_token: str = Header(...)) -> None:
    if x_bridge_token != settings.BIO_ERP_BRIDGE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid bridge token")


@router.post("/vendors", response_model=IngestResult)
async def ingest_vendors(
    payload: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_bridge_token),
):
    from app.models.supplier import Supplier
    accepted, rejected, errors = 0, 0, []
    for item in payload:
        try:
            existing = await db.execute(select(Supplier).where(Supplier.id == item.get("id")))
            if existing.scalar_one_or_none():
                accepted += 1
                continue
            vendor = Supplier(
                name_en=item.get("name", item.get("name_en", f"Vendor-{item.get('id')}")),
                name_ar=item.get("name_ar"),
                email=item.get("email"),
                phone1=item.get("phone"),
                address_en=item.get("address"),
                tax_id=item.get("tax_id"),
                service_category=item.get("category"),
                is_active=bool(item.get("is_active", True)),
                branch_id=1,
            )
            db.add(vendor)
            await db.flush()
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append(f"Vendor {item.get('id')}: {str(e)}")
    await db.commit()
    logger.info("Vendors ingested: %d accepted, %d rejected", accepted, rejected)
    return IngestResult(accepted=accepted, rejected=rejected, errors=errors)


@router.post("/gl-accounts", response_model=IngestResult)
async def ingest_gl_accounts(
    payload: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_bridge_token),
):
    from app.models.coa import COAAccount, COACategory
    accepted, rejected, errors = 0, 0, []
    for item in payload:
        try:
            existing = await db.execute(select(COAAccount).where(COAAccount.code == item.get("code")))
            if existing.scalar_one_or_none():
                accepted += 1
                continue
            result = await db.execute(select(COACategory).limit(1))
            default_cat = result.scalar_one_or_none()
            cat_id = default_cat.id if default_cat else 1
            account = COAAccount(
                code=item.get("code", f"EC-{item.get('id')}"),
                name_en=item.get("name", f"GL-{item.get('id')}"),
                category_id=cat_id,
                account_type=item.get("account_type", "Expense"),
                is_active=bool(item.get("is_active", True)),
            )
            db.add(account)
            await db.flush()
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append(f"GL {item.get('code', item.get('id'))}: {str(e)}")
    await db.commit()
    logger.info("GL accounts ingested: %d accepted, %d rejected", accepted, rejected)
    return IngestResult(accepted=accepted, rejected=rejected, errors=errors)


@router.post("/journal-entries", response_model=IngestResult)
async def ingest_journal_entries(
    payload: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_bridge_token),
):
    from app.models.finance import JVHeader, JVLine
    from app.models.coa import COAAccount
    accepted, rejected, errors = 0, 0, []
    for item in payload:
        try:
            jv_number = item.get("voucher_number", f"EC-JV-{item.get('id')}")
            existing = await db.execute(select(JVHeader).where(JVHeader.jv_number == jv_number))
            if existing.scalar_one_or_none():
                accepted += 1
                continue
            result = await db.execute(select(COAAccount).limit(1))
            default_gl = result.scalar_one_or_none()
            gl_id = default_gl.id if default_gl else 1
            raw_date = item.get("date")
            jv_date = date.fromisoformat(raw_date) if isinstance(raw_date, str) else (raw_date or date.today())
            jv = JVHeader(
                jv_number=jv_number,
                jv_date=jv_date,
                description=item.get("description", ""),
                total_debit=float(item.get("amount", 0)),
                total_credit=float(item.get("amount", 0)),
                status=item.get("status", "Posted"),
                branch_id=1,
            )
            db.add(jv)
            await db.flush()
            line = JVLine(
                jv_id=jv.id,
                line_number=1,
                gl_account_id=gl_id,
                debit_amount=float(item.get("amount", 0)),
                credit_amount=0,
                description=item.get("description", ""),
            )
            db.add(line)
            await db.flush()
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append(f"JV {item.get('voucher_number', item.get('id'))}: {str(e)}")
    await db.commit()
    logger.info("Journal entries ingested: %d accepted, %d rejected", accepted, rejected)
    return IngestResult(accepted=accepted, rejected=rejected, errors=errors)


@router.post("/invoices", response_model=IngestResult)
async def ingest_invoices(
    payload: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    _=Depends(verify_bridge_token),
):
    from app.models.finance import CustomerInvoice
    from app.models.client import Client
    accepted, rejected, errors = 0, 0, []
    for item in payload:
        try:
            inv_number = item.get("invoice_number")
            if inv_number:
                existing = await db.execute(select(CustomerInvoice).where(CustomerInvoice.invoice_number == inv_number))
                if existing.scalar_one_or_none():
                    accepted += 1
                    continue
            clients = await db.execute(select(Client).limit(1))
            default_client = clients.scalar_one_or_none()
            client_id = default_client.id if default_client else 1
            raw_issue = item.get("issue_date")
            raw_due = item.get("due_date")
            issue_date = date.fromisoformat(raw_issue) if isinstance(raw_issue, str) else (raw_issue or date.today())
            due_date = date.fromisoformat(raw_due) if isinstance(raw_due, str) else raw_due
            inv = CustomerInvoice(
                invoice_number=inv_number or f"EC-INV-{item.get('id')}",
                customer_id=client_id,
                invoice_date=issue_date,
                due_date=due_date,
                total_amount=float(item.get("total_amount", 0)),
                subtotal=float(item.get("total_amount", 0)),
                status=item.get("status", "Draft"),
                branch_id=1,
            )
            db.add(inv)
            await db.flush()
            accepted += 1
        except Exception as e:
            rejected += 1
            errors.append(f"INV {item.get('invoice_number', item.get('id'))}: {str(e)}")
    await db.commit()
    logger.info("Invoices ingested: %d accepted, %d rejected", accepted, rejected)
    return IngestResult(accepted=accepted, rejected=rejected, errors=errors)
