import random
import string
from datetime import datetime
from datetime import timezone
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession


class SerialNumberService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate(self, prefix: str, model_class, length: int = 4) -> str:
        year = datetime.utcnow().year
        result = await self.session.execute(
            select(func.count()).select_from(model_class)
        )
        count = result.scalar() or 0
        return f"{prefix}-{year}-{count + 1:0{length}d}"

    async def generate_event_code(self, model_class) -> str:
        year = datetime.utcnow().year
        result = await self.session.execute(
            text(f"SELECT COUNT(*) FROM {model_class.__tablename__}")
        )
        count = result.scalar() or 0
        return f"EVT-{year}-{count + 1:03d}"

    async def generate_pnr(self, model_class) -> str:
        chars = string.ascii_uppercase + string.digits
        pnr = "PNR-" + "".join(random.choices(chars, k=8))
        return pnr
