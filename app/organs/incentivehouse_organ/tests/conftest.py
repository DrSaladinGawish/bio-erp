"""
Pytest configuration for the IncentiveHouse ERP organ.

Provides fixtures for:
  * Temporary SQLite test database (per-test isolation, dropped on teardown)
  * Async + sync SQLAlchemy sessions against the test DB
  * Pre-seeded staging rows for the 5 modules
  * FastAPI TestClient (via httpx ASGITransport) against the organ's app
  * Auth token (admin) and headers

Tests look like::

    async def test_query_bnk_staging(client, auth_headers, seeded_bnk):
        resp = await client.get(
            "/incentivehouse/staging/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200

Environment variables:
  TEST_DATABASE_URL  - override the test DB URL
                       (default: ``sqlite+aiosqlite:///<tmpdir>/test.db``)
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import AsyncIterator, Iterator, Optional

import pytest

# ---------------------------------------------------------------------------
# Make the organ importable regardless of where pytest is invoked from
# ---------------------------------------------------------------------------
_THIS_DIR = Path(__file__).resolve().parent
_ORGAN_DIR = _THIS_DIR.parent
_PROJECT_ROOT = _ORGAN_DIR.parent.parent  # organ -> organs -> app
for p in (_PROJECT_ROOT, _ORGAN_DIR):
    p_str = str(p)
    if p_str not in sys.path:
        sys.path.insert(0, p_str)

# ---------------------------------------------------------------------------
# Default test DB = ephemeral SQLite (per test session)
# ---------------------------------------------------------------------------
_DEFAULT_TEST_DB = (
    "sqlite+aiosqlite:///" + str(Path(tempfile.gettempdir()) / "ih_test.db")
)
TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", _DEFAULT_TEST_DB)
TEST_SYNC_DATABASE_URL: str = os.getenv(
    "TEST_SYNC_DATABASE_URL",
    TEST_DATABASE_URL.replace("+asyncpg", "").replace("+aiosqlite", ""),
)

# Force the organ's modules to point at the test DB BEFORE importing app
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["SYNC_DATABASE_URL"] = TEST_SYNC_DATABASE_URL

# ---------------------------------------------------------------------------
# Imports (after env vars are set)
# ---------------------------------------------------------------------------
from app.organs.incentivehouse_organ import main as ih_main  # noqa: E402
from app.organs.incentivehouse_organ.models import (  # noqa: E402
    IncentiveBase, BnkStaging, SalStaging, PurStaging, EvnStaging, EnvStaging,
    STAGING_TABLE_NAMES,
)
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.orm import Session as SyncSession, sessionmaker  # noqa: E402

# Patch the organ's runtime DB URL to the test URL
ih_main.DATABASE_URL = TEST_DATABASE_URL
ih_main.SYNC_DATABASE_URL = TEST_SYNC_DATABASE_URL

# Build the FastAPI app once per session
APP = ih_main.create_app()


# ---------------------------------------------------------------------------
# Session-scoped event loop so async fixtures share connections
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Test database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_db_url() -> str:
    return TEST_DATABASE_URL


@pytest.fixture(scope="session")
def test_sync_db_url() -> str:
    return TEST_SYNC_DATABASE_URL


@pytest.fixture(scope="session")
def _sync_engine(test_sync_db_url: str):
    """Sync engine for DDL + seeding (one per session, disposed on teardown)."""
    connect_args = (
        {"check_same_thread": False} if "sqlite" in test_sync_db_url else {}
    )
    eng = create_engine(test_sync_db_url, echo=False, connect_args=connect_args)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session", autouse=True)
def _create_schema(_sync_engine) -> None:
    """Create all organ tables once for the whole test session."""
    IncentiveBase.metadata.create_all(bind=_sync_engine)
    # Auxiliary legacy tables (extraction_log, validation_log, etc.)
    aux_sql = [
        """CREATE TABLE IF NOT EXISTS extraction_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, module TEXT NOT NULL,
            source_file TEXT, user_id TEXT, status TEXT, extracted_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS validation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, extract_id INTEGER,
            user_id TEXT, status TEXT, quality_score REAL, validated_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS staging_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, validate_id INTEGER,
            target_table TEXT, user_id TEXT, snapshot_id TEXT, status TEXT,
            staged_at TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS reconcile_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, stage_id INTEGER,
            module TEXT, user_id TEXT, status TEXT,
            total_records INTEGER DEFAULT 0,
            reconciled_count INTEGER DEFAULT 0,
            mismatch_count INTEGER DEFAULT 0,
            unmatched_count INTEGER DEFAULT 0,
            reconciled_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS approval_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, recon_id INTEGER,
            approver_id TEXT, approval_level TEXT, status TEXT,
            approved_at TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS promotion_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, approve_id INTEGER,
            user_id TEXT, rollback_token TEXT, status TEXT, promoted_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS observe_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, promote_id INTEGER,
            user_id TEXT, status TEXT, metrics TEXT, observed_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS bnk_reconciliation (
            id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT,
            check_book_id INTEGER, check_book_name TEXT, bank_amount REAL,
            gl_amount REAL, variance REAL, recon_status TEXT,
            user_sub_led TEXT, user_type TEXT, user_keyword TEXT,
            user_notes TEXT)""",
    ]
    with _sync_engine.begin() as conn:
        for sql in aux_sql:
            conn.execute(text(sql))


@pytest.fixture
def sync_session(_sync_engine) -> Iterator[SyncSession]:
    """Sync session that rolls back at the end of the test."""
    session = SyncSession(bind=_sync_engine, autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
async def async_session(_create_schema) -> AsyncIterator[AsyncSession]:
    """Async session against the test DB (no rollback - schema is session-wide)."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    factory = async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        await session.close()
        await eng.dispose()


# ---------------------------------------------------------------------------
# Test data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seeded_bnk(sync_session: SyncSession) -> int:
    """Insert a BNK staging row and return its id."""
    from datetime import datetime
    row = BnkStaging(
        agent_id="test_agent",
        transaction_id="TRX-TEST-001",
        transaction_date=datetime.now().isoformat(),
        account_code="1100",
        description="Test BNK staging record",
        debit_amount=100.0,
        credit_amount=0.0,
        currency="EGP",
        validation_status="PASS",
    )
    sync_session.add(row)
    sync_session.commit()
    sync_session.refresh(row)
    return row.id


@pytest.fixture
def seeded_all_modules(sync_session: SyncSession) -> dict:
    """Insert one row in each of the 5 staging tables; return id map."""
    from datetime import datetime
    models = {
        "Bnk": BnkStaging, "Sal": SalStaging, "Pur": PurStaging,
        "Evn": EvnStaging, "Env": EnvStaging,
    }
    ids: dict = {}
    for mod, Model in models.items():
        row = Model(
            agent_id="test_agent",
            transaction_id=f"TRX-TEST-{mod}",
            transaction_date=datetime.now().isoformat(),
            account_code="9999",
            description=f"Test {mod} staging record",
            debit_amount=50.0, credit_amount=0.0, currency="EGP",
            validation_status="PASS",
        )
        sync_session.add(row)
        sync_session.flush()
        ids[mod] = row.id
    sync_session.commit()
    return ids


# ---------------------------------------------------------------------------
# HTTP client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    """The organ's FastAPI app."""
    return APP


@pytest.fixture
async def client(app) -> AsyncIterator:
    """Async HTTP client against the organ's FastAPI app (no network)."""
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sync_client(app) -> Iterator:
    """Sync TestClient (useful for SSE / streaming / WebSocket tests)."""
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_token(sync_client) -> str:
    """Login as admin and return a token usable in the ``token=`` query param."""
    resp = sync_client.post(
        "/v2/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    return ""


@pytest.fixture
def auth_headers(auth_token) -> dict:
    if auth_token:
        # v2 routes use ?token=... not Bearer headers
        return {"X-Test-Token": auth_token}
    return {}


# ---------------------------------------------------------------------------
# Engine reset (so each test can choose to start from a clean slate)
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_staging_tables(sync_session: SyncSession):
    """Truncate all staging + lifecycle tables for tests that need a clean DB."""
    for table in STAGING_TABLE_NAMES.values():
        try:
            sync_session.execute(text(f"DELETE FROM {table}"))
        except Exception:
            pass
    for aux in (
        "extraction_log", "validation_log", "staging_log", "reconcile_log",
        "approval_log", "promotion_log", "observe_log", "bnk_reconciliation",
    ):
        try:
            sync_session.execute(text(f"DELETE FROM {aux}"))
        except Exception:
            pass
    sync_session.commit()
    yield
