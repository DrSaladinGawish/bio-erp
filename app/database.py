from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

async_engine = None
_async_session_factory = None

readonly_engine = None
_readonly_session_factory = None

sync_engine = None
_sync_session_factory = None


class Base(DeclarativeBase):
    pass


class IHEBase(DeclarativeBase):
    """Separate declarative base for ihe_models (dbo schema, SQL Server compat)."""

    pass


def get_async_engine():
    global async_engine
    if async_engine is None:
        async_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
        )
    return async_engine


def get_async_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


# Alias for USB compatibility (lazy-initialized)
class _AsyncSessionLocal:
    def __call__(self):
        return get_async_session_factory()()


AsyncSessionLocal = _AsyncSessionLocal()


def get_readonly_async_engine():
    global readonly_engine
    if readonly_engine is None:
        readonly_engine = create_async_engine(
            settings.DATABASE_URL_READONLY,
            echo=settings.DEBUG,
            pool_size=5,
            max_overflow=5,
        )
    return readonly_engine


def get_readonly_session_factory():
    global _readonly_session_factory
    if _readonly_session_factory is None:
        _readonly_session_factory = async_sessionmaker(
            get_readonly_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _readonly_session_factory


async def get_readonly_db():
    factory = get_readonly_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()


async def get_db():
    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()


def get_sync_engine():
    global sync_engine
    if sync_engine is None:
        sync_url = settings.DATABASE_URL.replace("+asyncpg", "").replace(
            "+aiosqlite", ""
        )
        sync_engine = create_engine(sync_url, echo=settings.DEBUG)
    return sync_engine


def get_sync_session():
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(bind=get_sync_engine())
    return _sync_session_factory()


def init_db():
    from app.database import IHEBase
    from app.models import Base as ModelsBase

    sync_eng = get_sync_engine()
    ModelsBase.metadata.create_all(bind=sync_eng)
    IHEBase.metadata.create_all(bind=sync_eng)


def drop_db():
    from app.database import IHEBase
    from app.models import Base as ModelsBase

    sync_eng = get_sync_engine()
    ModelsBase.metadata.drop_all(bind=sync_eng)
    IHEBase.metadata.drop_all(bind=sync_eng)
