"""Pytest configuration for BIO_ERP v5.

Design:
  - Sync engine (no event loop) handles DDL + seed data at module load.
  - ``loop_scope="session"`` via module-level pytestmark makes all async
    fixtures and tests share one event loop — no loop mismatch.
  - Single async engine pool shared via ``get_async_engine()``.
  - Engine pool is disposed after each test to prevent stale connections.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession
from sqlalchemy.orm import Session as SyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp_test",
)

# ── Override settings BEFORE any app module uses it ───────────────
os.environ["DATABASE_URL"] = TEST_DB_URL
from app.config import settings
settings.DATABASE_URL = TEST_DB_URL

# Import app AFTER settings are patched
from app.main import app  # noqa: E402


# ── Sync DB setup (no event loop needed) ──────────────────────────
_sync_url = TEST_DB_URL.replace("+asyncpg", "")
_sync_engine = create_engine(_sync_url, echo=False)

# Create all tables
from app.models import Base  # noqa: E402
Base.metadata.create_all(bind=_sync_engine)

# Seed admin / currency / branch
from app.auth import hash_password  # noqa: E402
from app.models import Branch, Currency, User  # noqa: E402

with SyncSession(_sync_engine) as session:
    with session.begin():
        cur = session.execute(text("SELECT id FROM currencies WHERE code = 'USD'"))
        currency_id = cur.scalar()
        if not currency_id:
            session.add(Currency(code="USD", name_en="US Dollar", symbol="$",
                                 is_base=True, mid_rate=1.0, buy_rate=1.0,
                                 sell_rate=1.0, decimal_places=2))
            session.flush()
            currency_id = session.execute(
                text("SELECT id FROM currencies WHERE code = 'USD'")
            ).scalar()

        br = session.execute(text("SELECT id FROM branches WHERE code = 'HQ'"))
        branch_id = br.scalar()
        if not branch_id:
            session.add(Branch(code="HQ", name_en="Headquarters", country="US",
                               currency_id=currency_id, is_hq=True, vat_rate=0.0))
            session.flush()
            branch_id = session.execute(
                text("SELECT id FROM branches WHERE code = 'HQ'")
            ).scalar()

        usr = session.execute(text("SELECT id FROM users WHERE username = 'admin'"))
        if not usr.scalar():
            session.add(User(
                username="admin", email="admin@bioerp.local",
                hashed_password=hash_password("admin123"),
                full_name_en="System Admin", is_superuser=True,
                branch_id=branch_id,
            ))


# ── Async fixtures (all use the app's async engine) ───────────────

@pytest.fixture
async def db_connection():
    """Per-test connection with transaction rollback."""
    from app.database import get_async_engine
    engine = get_async_engine()
    conn = await engine.connect()
    trans = await conn.begin()
    try:
        yield conn
    finally:
        await trans.rollback()
        await conn.close()
        await engine.dispose()


@pytest.fixture
async def db_session(db_connection: AsyncConnection):
    """Per-test AsyncSession bound to the rollback connection."""
    session = AsyncSession(bind=db_connection, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
async def client():
    """HTTP client against the FastAPI app (no network)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    # Dispose the engine pool so the next test starts fresh
    from app.database import get_async_engine
    await get_async_engine().dispose()


# ── Auth fixtures ─────────────────────────────────────────────────

@pytest.fixture
async def auth_token(client):
    """Valid JWT access_token for the seeded admin user."""
    resp = await client.post(
        "/api/v1/accounting/login",
        json={"username": "admin", "password": "admin123"},
    )
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    return ""


@pytest.fixture
async def auth_headers(auth_token):
    """Authorization header dict for authenticated requests."""
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}
