"""Tests for bank reconciliation auto-reconcile feature (v2.4.2)."""
from __future__ import annotations

import os

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session as SyncSession

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp_test",
)
_sync_url = TEST_DB_URL.replace("+asyncpg", "")
_sync_engine = create_engine(_sync_url, echo=False)


@pytest.fixture
def seeded_session():
    from datetime import datetime, timezone
    from app.models import COAAccount, COACategory, BankImportSession, BankStaging

    with SyncSession(_sync_engine) as session, session.begin():
        cat = session.execute(
            text("SELECT id FROM coa_categories WHERE code = 'TEST'")
        ).scalar()
        if not cat:
            c = COACategory(code="TEST", name_en="Test Category")
            session.add(c)
            session.flush()
            cat = c.id

        acct = COAAccount(
            code="1100-BNK",
            name_en="Test Bank COA",
            category_id=cat,
            account_type="Asset",
        )
        session.add(acct)
        session.flush()

        sess = BankImportSession(
            bank_account_id=acct.id,
            file_name="test_import.csv",
            total_transactions=2,
            matched_count=0,
            unmatched_count=2,
            status="IMPORTED",
        )
        session.add(sess)
        session.flush()

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        txn1 = BankStaging(
            session_id=sess.id,
            transaction_date=now,
            description="Test payment",
            debit_amount=1000.0,
            credit_amount=0.0,
            reference="REF001",
            is_matched=False,
        )
        txn2 = BankStaging(
            session_id=sess.id,
            transaction_date=now,
            description="Test receipt",
            debit_amount=0.0,
            credit_amount=500.0,
            reference="REF002",
            is_matched=False,
        )
        session.add_all([txn1, txn2])
        session.flush()
        session_id = sess.id

    yield {"session_id": session_id}

    with SyncSession(_sync_engine) as session, session.begin():
        session.execute(
            text("DELETE FROM bank_trnx_staging WHERE session_id = :sid"),
            {"sid": session_id},
        )
        session.execute(
            text("DELETE FROM bank_import_sessions WHERE id = :sid"),
            {"sid": session_id},
        )
        session.execute(
            text("DELETE FROM coa_accounts WHERE code = '1100-BNK'"),
        )


async def test_auto_reconcile_success(
    client: AsyncClient, auth_headers: dict, seeded_session: dict
):
    session_id = seeded_session["session_id"]
    resp = await client.post(
        f"/api/v1/bank-reconciliation/auto-reconcile/{session_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["total_unmatched"] == 2
    assert "auto_matched" in data
    assert "still_unmatched" in data


async def test_auto_reconcile_not_found(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.post(
        "/api/v1/bank-reconciliation/auto-reconcile/99999",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_reconciliation_status(
    client: AsyncClient, auth_headers: dict, seeded_session: dict
):
    session_id = seeded_session["session_id"]
    resp = await client.get(
        f"/api/v1/bank-reconciliation/reconciliation-status/{session_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == session_id
    assert data["total_transactions"] == 2
    assert "matched" in data
    assert "unmatched" in data


async def test_reconciliation_status_not_found(
    client: AsyncClient, auth_headers: dict
):
    resp = await client.get(
        "/api/v1/bank-reconciliation/reconciliation-status/99999",
        headers=auth_headers,
    )
    assert resp.status_code == 404


async def test_auto_reconcile_requires_auth(
    client: AsyncClient, seeded_session: dict
):
    session_id = seeded_session["session_id"]
    resp = await client.post(
        f"/api/v1/bank-reconciliation/auto-reconcile/{session_id}",
    )
    assert resp.status_code == 403
