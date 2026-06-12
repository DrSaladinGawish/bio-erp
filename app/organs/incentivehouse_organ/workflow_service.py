from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models_empty_modules import ApprovalInstance, ApprovalRule, ApprovalStep

logger = logging.getLogger(__name__)


async def submit_for_approval(
    session: AsyncSession,
    module: str,
    document_type: str,
    document_id: int,
    document_number: str,
    amount: float,
    requested_by: int,
) -> dict:
    rules_result = await session.execute(
        select(ApprovalRule)
        .where(
            and_(
                ApprovalRule.module == module,
                ApprovalRule.document_type == document_type,
                ApprovalRule.min_amount <= amount,
                or_(ApprovalRule.max_amount.is_(None), ApprovalRule.max_amount >= amount),
                ApprovalRule.is_active == True,
            )
        )
        .order_by(ApprovalRule.sequence, ApprovalRule.priority)
    )
    rules = rules_result.scalars().all()

    if not rules:
        return {"status": "NO_APPROVAL_REQUIRED", "message": "No approval rules match", "instance_id": None}

    instance = ApprovalInstance(
        module=module,
        document_id=document_id,
        document_number=document_number,
        requested_by=requested_by,
        amount=amount,
        status="PENDING",
        current_step=1,
        total_steps=len(rules),
    )
    session.add(instance)
    await session.flush()

    for i, rule in enumerate(rules):
        step = ApprovalStep(
            instance_id=instance.id,
            sequence=i + 1,
            rule_id=rule.id,
            approver_id=rule.user_id,
            role_id=rule.role_id,
            status="PENDING" if i == 0 else "WAITING",
            due_at=datetime.utcnow() + timedelta(hours=rule.escalation_hours or 48),
        )
        session.add(step)

    await session.commit()
    return {"status": "PENDING", "instance_id": instance.id, "total_steps": len(rules)}


async def approve_step(
    session: AsyncSession,
    instance_id: int,
    step_sequence: int,
    approver_id: int,
    comments: Optional[str] = None,
) -> dict:
    result = await session.execute(
        select(ApprovalStep).where(
            ApprovalStep.instance_id == instance_id,
            ApprovalStep.sequence == step_sequence,
            ApprovalStep.status == "PENDING",
        )
    )
    step = result.scalar_one_or_none()
    if not step:
        return {"status": "ERROR", "message": f"No pending step {step_sequence} found for instance {instance_id}"}

    step.status = "APPROVED"
    step.decision = "APPROVED"
    step.acted_at = datetime.utcnow()
    if comments:
        step.comments = comments

    result = await session.execute(select(ApprovalStep).where(
        ApprovalStep.instance_id == instance_id,
        ApprovalStep.sequence == step_sequence + 1,
    ))
    next_step = result.scalar_one_or_none()

    result = await session.execute(
        select(ApprovalInstance).where(ApprovalInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()

    if next_step:
        next_step.status = "PENDING"
        instance.current_step = step_sequence + 1
        await session.commit()
        return {"status": "APPROVED_STEP", "instance_id": instance_id, "next_step": step_sequence + 1, "total_steps": instance.total_steps}
    else:
        instance.status = "APPROVED"
        instance.current_step = step_sequence
        instance.completed_at = datetime.utcnow()
        await session.commit()
        return {"status": "FULLY_APPROVED", "instance_id": instance_id}


async def reject_step(
    session: AsyncSession,
    instance_id: int,
    step_sequence: int,
    approver_id: int,
    comments: str = "Rejected",
) -> dict:
    result = await session.execute(
        select(ApprovalStep).where(
            ApprovalStep.instance_id == instance_id,
            ApprovalStep.sequence == step_sequence,
            ApprovalStep.status == "PENDING",
        )
    )
    step = result.scalar_one_or_none()
    if not step:
        return {"status": "ERROR", "message": f"No pending step {step_sequence} found"}

    step.status = "REJECTED"
    step.decision = "REJECTED"
    step.comments = comments
    step.acted_at = datetime.utcnow()

    result = await session.execute(
        select(ApprovalInstance).where(ApprovalInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    instance.status = "REJECTED"
    instance.completed_at = datetime.utcnow()
    await session.commit()
    return {"status": "REJECTED", "instance_id": instance_id}


async def get_workflow_status(
    session: AsyncSession,
    instance_id: int,
) -> Optional[dict]:
    result = await session.execute(
        select(ApprovalInstance).where(ApprovalInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        return None

    steps_result = await session.execute(
        select(ApprovalStep)
        .where(ApprovalStep.instance_id == instance_id)
        .order_by(ApprovalStep.sequence)
    )
    steps = steps_result.scalars().all()

    return {
        "id": instance.id,
        "module": instance.module,
        "document_id": instance.document_id,
        "document_number": instance.document_number,
        "amount": float(instance.amount or 0),
        "status": instance.status,
        "current_step": instance.current_step,
        "total_steps": instance.total_steps,
        "requested_by": instance.requested_by,
        "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
        "created_at": instance.created_at.isoformat() if instance.created_at else None,
        "steps": [
            {
                "sequence": s.sequence,
                "status": s.status,
                "decision": s.decision,
                "comments": s.comments,
                "acted_at": s.acted_at.isoformat() if s.acted_at else None,
                "due_at": s.due_at.isoformat() if s.due_at else None,
            }
            for s in steps
        ],
    }


async def list_pending_approvals(
    session: AsyncSession,
    approver_role: Optional[str] = None,
    module: Optional[str] = None,
) -> list[dict]:
    stmt = select(ApprovalStep).join(
        ApprovalInstance,
        ApprovalStep.instance_id == ApprovalInstance.id,
    ).where(
        ApprovalStep.status == "PENDING",
    )
    if module:
        stmt = stmt.where(ApprovalInstance.module == module)
    stmt = stmt.order_by(ApprovalInstance.created_at.desc())
    result = await session.execute(stmt)
    steps = result.scalars().all()

    seen = set()
    instances = []
    for s in steps:
        if s.instance_id not in seen:
            seen.add(s.instance_id)
            status = await get_workflow_status(session, s.instance_id)
            if status:
                instances.append(status)
    return instances
