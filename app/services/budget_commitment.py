from datetime import datetime
from datetime import timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.event_budget_ext import BudgetCommitment
from app.models.event import EventBudgetLine


class BudgetCommitmentManager:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def commit_budget(
        self,
        event_id: int,
        budget_version: int,
        source_type: str,
        source_id: int,
        source_number: str,
        amount: float,
        budget_line_id: int | None = None,
    ) -> BudgetCommitment:
        commitment = BudgetCommitment(
            event_id=event_id,
            budget_version=budget_version,
            budget_line_id=budget_line_id,
            source_type=source_type,
            source_id=source_id,
            source_number=source_number,
            amount=amount,
            status="committed",
        )
        self.db.add(commitment)
        await self.db.commit()
        return commitment

    async def release_commitment(self, commitment_id: int) -> bool:
        result = await self.db.execute(
            select(BudgetCommitment).where(BudgetCommitment.id == commitment_id)
        )
        commitment = result.scalar_one_or_none()
        if not commitment or commitment.status != "committed":
            return False
        commitment.status = "released"
        commitment.released_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.db.commit()
        return True

    async def consume_commitment(
        self, commitment_id: int, actual_amount: float
    ) -> bool:
        result = await self.db.execute(
            select(BudgetCommitment).where(BudgetCommitment.id == commitment_id)
        )
        commitment = result.scalar_one_or_none()
        if not commitment or commitment.status != "committed":
            return False
        commitment.status = "consumed"
        commitment.consumed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await self.db.commit()
        return True

    async def get_budget_status(self, event_id: int, budget_version: int) -> dict:
        result = await self.db.execute(
            select(BudgetCommitment).where(
                BudgetCommitment.event_id == event_id,
                BudgetCommitment.budget_version == budget_version,
            )
        )
        commitments = result.scalars().all()
        total_budget = 0.0
        total_committed = sum(c.amount for c in commitments if c.status == "committed")
        total_consumed = sum(c.amount for c in commitments if c.status == "consumed")
        total_released = sum(c.amount for c in commitments if c.status == "released")

        lines_result = await self.db.execute(
            select(EventBudgetLine).where(
                EventBudgetLine.event_id == event_id,
                EventBudgetLine.budget_version == budget_version,
            )
        )
        lines = lines_result.scalars().all()
        total_budget = sum(line.total_cost for line in lines)

        return {
            "event_id": event_id,
            "budget_version": budget_version,
            "total_budget": total_budget,
            "total_committed": total_committed,
            "total_consumed": total_consumed,
            "total_released": total_released,
            "remaining": total_budget - total_committed - total_consumed,
            "commitment_count": len(commitments),
        }
