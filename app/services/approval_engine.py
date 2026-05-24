from datetime import datetime
from datetime import timezone, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import ApprovalRule, ApprovalInstance, ApprovalStep


class ApprovalEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_approval_instance(
        self,
        document_type: str,
        document_id: int,
        document_number: str,
        requester_id: int,
        amount: float,
    ) -> ApprovalInstance | None:
        result = await self.db.execute(
            select(ApprovalRule)
            .where(
                and_(
                    ApprovalRule.document_type == document_type,
                    ApprovalRule.is_active,
                    ApprovalRule.min_amount <= amount,
                    or_(
                        ApprovalRule.max_amount is None,
                        ApprovalRule.max_amount >= amount,
                    ),
                )
            )
            .order_by(ApprovalRule.sequence)
        )
        rules = result.scalars().all()
        if not rules:
            return None

        instance = ApprovalInstance(
            document_type=document_type,
            document_id=document_id,
            document_number=document_number,
            requester_id=requester_id,
            total_amount=amount,
            status="pending",
            current_step=1,
            total_steps=len(rules),
        )
        self.db.add(instance)
        await self.db.flush()

        for idx, rule in enumerate(rules, 1):
            self.db.add(
                ApprovalStep(
                    instance_id=instance.id,
                    sequence=idx,
                    rule_id=rule.id,
                    approver_id=rule.user_id,
                    role_id=rule.role_id,
                    status="pending",
                    due_at=datetime.utcnow()
                    + timedelta(hours=rule.escalation_hours),
                )
            )

        await self.db.commit()
        return instance

    async def process_action(
        self, step_id: int, instance_id: int, action: str, user_id: int
    ) -> dict:
        result = await self.db.execute(
            select(ApprovalStep).where(
                ApprovalStep.id == step_id, ApprovalStep.instance_id == instance_id
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            return {"success": False, "message": "Approval step not found"}

        result = await self.db.execute(
            select(ApprovalInstance).where(ApprovalInstance.id == instance_id)
        )
        instance = result.scalar_one_or_none()

        if action == "approve":
            step.status = "approved"
            step.decision = "approve"
            step.acted_at = datetime.utcnow()
            step.approver_id = user_id

            result = await self.db.execute(
                select(ApprovalStep).where(
                    ApprovalStep.instance_id == instance.id,
                    ApprovalStep.status == "pending",
                )
            )
            pending = result.scalars().all()
            if not pending:
                instance.status = "approved"
                instance.completed_at = datetime.utcnow()
            else:
                instance.current_step += 1

        elif action == "reject":
            step.status = "rejected"
            step.decision = "reject"
            step.acted_at = datetime.utcnow()
            step.approver_id = user_id
            instance.status = "rejected"
            instance.completed_at = datetime.utcnow()

        elif action == "escalate":
            step.status = "escalated"
            result = await self.db.execute(
                select(ApprovalRule).where(ApprovalRule.id == step.rule_id)
            )
            rule = result.scalar_one_or_none()
            if rule and rule.escalation_role_id:
                step.role_id = rule.escalation_role_id
                step.approver_id = None
                step.due_at = datetime.utcnow() + timedelta(hours=24)

        await self.db.commit()
        return {
            "success": True,
            "instance_status": instance.status,
            "message": f"Action {action} processed",
        }

    async def get_pending_approvals(self, user_id: int) -> list[dict]:
        result = await self.db.execute(
            select(ApprovalStep)
            .join(ApprovalInstance)
            .where(
                ApprovalStep.status == "pending",
                or_(
                    ApprovalStep.approver_id == user_id,
                ),
            )
        )
        steps = result.scalars().all()
        instance_ids = list(set(s.instance_id for s in steps))
        if not instance_ids:
            return []

        result = await self.db.execute(
            select(ApprovalInstance).where(ApprovalInstance.id.in_(instance_ids))
        )
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
