"""
IncentiveHouse ERP — Database session dependency for async routers.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.organs.incentivehouse_organ.db import get_async_session_factory


async def get_async_session() -> AsyncSession:
    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()
