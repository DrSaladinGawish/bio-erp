import random
import string
from datetime import datetime
from datetime import timezone
from sqlalchemy import select, func, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workflow import DocumentSequence


class SerialNumberService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate(self, prefix: str, model_class=None, length: int = 4) -> str:
        year = datetime.now(timezone.utc).replace(tzinfo=None).year
        # Atomically increment DocumentSequence if a matching row exists
        doc_type = prefix.upper()
        result = await self.session.execute(
            select(DocumentSequence).where(DocumentSequence.prefix == f"{doc_type}-")
        )
        seq = result.scalar_one_or_none()
        if seq:
            await self.session.execute(
                update(DocumentSequence)
                .where(DocumentSequence.id == seq.id)
                .values(current_number=DocumentSequence.current_number + 1)
            )
            await self.session.flush()
            await self.session.refresh(seq)
            count = seq.current_number
            padding = seq.padding or length
        else:
            result = await self.session.execute(
                select(func.count()).select_from(model_class) if model_class else select(func.count())
            )
            count = (result.scalar() or 0) + 1
            padding = length
        return f"{doc_type}-{year}-{count:0{padding}d}"

    async def generate_event_code(self, model_class) -> str:
        year = datetime.now(timezone.utc).replace(tzinfo=None).year
        result = await self.session.execute(
            text(f"SELECT COUNT(*) FROM {model_class.__tablename__}")
        )
        count = result.scalar() or 0
        return f"EVT-{year}-{count + 1:03d}"

    async def generate_pnr(self, model_class=None) -> str:
        chars = string.ascii_uppercase + string.digits
        pnr = "PNR-" + "".join(random.choices(chars, k=8))
        return pnr
