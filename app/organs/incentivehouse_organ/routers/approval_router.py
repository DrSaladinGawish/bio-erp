from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..models_empty_modules import ApprovalInstance, ApprovalRule, ApprovalStep
from ..workflow_service import (
    approve_step,
    get_workflow_status,
    list_pending_approvals,
    reject_step,
    submit_for_approval,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/workflow", tags=["Workflow / Approval"])


class SubmitRequest(BaseModel):
    module: str
    document_type: str
    document_id: int
    document_number: str
    amount: float = 0.0
    requested_by: int


class ActionRequest(BaseModel):
    approver_id: int
    comments: Optional[str] = None


@router.post("/submit")
async def submit(
    payload: SubmitRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    return await submit_for_approval(
        session, payload.module, payload.document_type,
        payload.document_id, payload.document_number,
        payload.amount, payload.requested_by,
    )


@router.post("/approve/{instance_id}/{step_sequence}")
async def approve(
    instance_id: int,
    step_sequence: int,
    payload: ActionRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    return await approve_step(session, instance_id, step_sequence, payload.approver_id, payload.comments)


@router.post("/reject/{instance_id}/{step_sequence}")
async def reject(
    instance_id: int,
    step_sequence: int,
    payload: ActionRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    return await reject_step(session, instance_id, step_sequence, payload.approver_id, payload.comments or "Rejected")


@router.get("/status/{instance_id}")
async def status(
    instance_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    result = await get_workflow_status(session, instance_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Workflow instance {instance_id} not found")
    return result


@router.get("/pending")
async def pending(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    module: Annotated[Optional[str], Query()] = None,
):
    return {"data": await list_pending_approvals(session, module=module)}


@router.get("/rules")
async def list_rules(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    module: Annotated[Optional[str], Query()] = None,
):
    stmt = select(ApprovalRule).order_by(ApprovalRule.module, ApprovalRule.sequence, ApprovalRule.priority)
    if module:
        stmt = stmt.where(ApprovalRule.module == module)
    rows = (await session.execute(stmt)).scalars().all()
    return {"data": [{"id": r.id, "module": r.module, "document_type": r.document_type, "min_amount": r.min_amount, "max_amount": r.max_amount, "approver_role": r.approver_role, "sequence": r.sequence} for r in rows], "total": len(rows)}


@router.get("/instances")
async def list_instances(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    status_filter: Annotated[Optional[str], Query(alias="status")] = None,
    module: Annotated[Optional[str], Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 50,
):
    stmt = select(ApprovalInstance)
    filters = []
    if status_filter:
        filters.append(ApprovalInstance.status == status_filter)
    if module:
        filters.append(ApprovalInstance.module == module)
    if filters:
        stmt = stmt.where(*filters)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(ApprovalInstance.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await session.execute(stmt)).scalars().all()
    return {
        "data": [{"id": r.id, "module": r.module, "document_id": r.document_id, "document_number": r.document_number, "amount": float(r.amount or 0), "status": r.status, "current_step": r.current_step, "total_steps": r.total_steps, "created_at": str(r.created_at) if r.created_at else None} for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/summary")
async def summary(
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    rules = (await session.execute(select(func.count(ApprovalRule.id)))).scalar() or 0
    pending = (await session.execute(select(func.count(ApprovalInstance.id)).where(ApprovalInstance.status == "PENDING"))).scalar() or 0
    approved = (await session.execute(select(func.count(ApprovalInstance.id)).where(ApprovalInstance.status == "APPROVED"))).scalar() or 0
    rejected = (await session.execute(select(func.count(ApprovalInstance.id)).where(ApprovalInstance.status == "REJECTED"))).scalar() or 0
    return {"total_rules": rules, "pending": pending, "approved": approved, "rejected": rejected}
