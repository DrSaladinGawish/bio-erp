"""
IncentiveHouse ERP - Database Engines & Session Factories
=========================================================
Extracted from main.py to break the circular import chain:

    main â†’ bnk_router â†’ main  (BROKEN)
    main â†’ sub_app â†’ recon_api â†’ main (BROKEN)

All three now import ``get_sync_session_factory`` from this module instead.
"""
from __future__ import annotations

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "sqlite+aiosqlite:///./protocell_staging.db"
)
SYNC_DATABASE_URL: str = os.getenv(
    "SYNC_DATABASE_URL",
    DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", ""),
)

_async_engine = None
_async_session_factory: Optional[async_sessionmaker] = None
_sync_engine: Optional[Engine] = None
_sync_session_factory: Optional[sessionmaker] = None


def get_async_engine():
    global _async_engine
    if _async_engine is None:
        connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
        engine_kwargs = dict(echo=False, connect_args=connect_args)
        if "sqlite" not in DATABASE_URL:
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10
        _async_engine = create_async_engine(DATABASE_URL, **engine_kwargs)
    return _async_engine


def get_async_session_factory() -> async_sessionmaker:
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


def get_sync_engine() -> Engine:
    global _sync_engine
    if _sync_engine is None:
        connect_args = {"check_same_thread": False} if "sqlite" in SYNC_DATABASE_URL else {}
        _sync_engine = create_engine(
            SYNC_DATABASE_URL,
            echo=False,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
    return _sync_engine


def get_sync_session_factory() -> sessionmaker:
    global _sync_session_factory
    if _sync_session_factory is None:
        _sync_session_factory = sessionmaker(
            bind=get_sync_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _sync_session_factory


async def get_async_db():
    factory = get_async_session_factory()
    session = factory()
    try:
        yield session
    finally:
        await session.close()


def get_db():
    factory = get_sync_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
