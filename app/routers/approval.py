from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models.auth import User
from app.models.workflow import (
    ApprovalRule,
    ApprovalInstance,
    ApprovalStep,
    DocumentSequence,
)
from app.services.approval_engine import ApprovalEngine

router = APIRouter(prefix="/api/v1/approval", tags=["Approval Workflow"])


# --- Approval Rules ---


class ApprovalRuleCreate(BaseModel):
    document_type: str
    min_amount: float = 0.0
    max_amount: float | None = None
    role_id: int
    user_id: int | None = None
    sequence: int = 1
    is_mandatory: bool = True
    can_delegate: bool = True
    escalation_hours: int = 24
    escalation_role_id: int | None = None


@router.post("/rules")
async def create_approval_rule(
    req: ApprovalRuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("approval.manage")),
):
    rule = ApprovalRule(**req.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": rule.id, "document_type": rule.document_type}


@router.get("/rules")
async def list_approval_rules(
    document_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("approval.read")),
):
    query = select(ApprovalRule).where(ApprovalRule.is_active)
    if document_type:
        query = query.where(ApprovalRule.document_type == document_type)
    query = query.order_by(ApprovalRule.document_type, ApprovalRule.sequence)
    result = await db.execute(query)
    rules = result.scalars().all()
    return [
        {
            "id": r.id,
            "document_type": r.document_type,
            "min_amount": r.min_amount,
            "max_amount": r.max_amount,
            "role_id": r.role_id,
            "sequence": r.sequence,
            "escalation_hours": r.escalation_hours,
        }
        for r in rules
    ]


# --- Approval Instances ---


@router.get("/instances")
async def list_approval_instances(
    status: str | None = Query(None),
    document_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("approval.read")),
):
    query = (
        select(ApprovalInstance)
        .order_by(ApprovalInstance.created_at.desc())
        .limit(limit)
    )
    if status:
        query = query.where(ApprovalInstance.status == status)
    if document_type:
        query = query.where(ApprovalInstance.document_type == document_type)
    result = await db.execute(query)
    instances = result.scalars().all()
    return [
        {
            "id": i.id,
            "document_type": i.document_type,
            "document_number": i.document_number,
            "total_amount": i.total_amount,
            "status": i.status,
            "current_step": i.current_step,
            "total_steps": i.total_steps,
            "created_at": i.created_at,
        }
        for i in instances
    ]


@router.get("/instances/{instance_id}")
async def get_approval_instance(
    instance_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("approval.read")),
):
    result = await db.execute(
        select(ApprovalInstance).where(ApprovalInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(404, detail="Approval instance not found")

    steps_result = await db.execute(
        select(ApprovalStep)
        .where(ApprovalStep.instance_id == instance_id)
        .order_by(ApprovalStep.sequence)
    )
    steps = steps_result.scalars().all()

    return {
        "id": instance.id,
        "document_type": instance.document_type,
        "document_number": instance.document_number,
        "total_amount": instance.total_amount,
        "status": instance.status,
        "current_step": instance.current_step,
        "total_steps": instance.total_steps,
        "created_at": instance.created_at,
        "completed_at": instance.completed_at,
        "steps": [
            {
                "id": s.id,
                "sequence": s.sequence,
                "approver_id": s.approver_id,
                "status": s.status,
                "decision": s.decision,
                "comments": s.comments,
                "acted_at": s.acted_at,
                "due_at": s.due_at,
            }
            for s in steps
        ],
    }


# --- Approval Actions ---


class ApprovalActionRequest(BaseModel):
    instance_id: int
    step_id: int
    action: str
    comments: str | None = None


@router.post("/actions")
async def process_approval_action(
    req: ApprovalActionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("approval.approve")),
):
    engine = ApprovalEngine(db)
    result = await engine.process_action(
        step_id=req.step_id,
        instance_id=req.instance_id,
        action=req.action,
        user_id=user.id,
    )
    if not result["success"]:
        raise HTTPException(400, detail=result["message"])
    return result


@router.get("/pending")
async def get_pending_approvals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("approval.read")),
):
    engine = ApprovalEngine(db)
    return await engine.get_pending_approvals(user_id=user.id)


# --- Document Sequence ---


class DocumentSequenceCreate(BaseModel):
    document_type: str
    prefix: str | None = None
    suffix: str | None = None
    padding: int = 5


@router.post("/sequences")
async def create_document_sequence(
    req: DocumentSequenceCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("approval.manage")),
):
    seq = DocumentSequence(**req.model_dump())
    db.add(seq)
    await db.commit()
    await db.refresh(seq)
    return {"id": seq.id, "document_type": seq.document_type, "prefix": seq.prefix}


@router.get("/sequences")
async def list_document_sequences(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("approval.read")),
):
    result = await db.execute(
        select(DocumentSequence).where(DocumentSequence.is_active)
    )
    return result.scalars().all()
