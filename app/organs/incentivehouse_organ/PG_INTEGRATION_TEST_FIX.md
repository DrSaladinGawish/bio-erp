PG_INTEGRATION_TEST_FIX.md - PostgreSQL Integration Test Mismatch
====================================================================

PROBLEM:
--------
The PG integration test targets /api/v1/incentivehouse/auth/login (root app pattern)
but the organ dev server uses sub_app.py's login at /login.
The test is designed for the root Bio-ERP app on port 8000 against PostgreSQL data --
not the organ's standalone SQLite dev server on port 8001.

SOLUTION:
---------
Create TWO test suites:

1. ORGAN DEV TESTS (SQLite, port 8001) -- Already passing (178 tests)
   - Tests run against sub_app.py standalone
   - Auth endpoint: POST /login
   - No PostgreSQL required
   - Use: pytest tests/organ/ -v

2. ROOT APP INTEGRATION TESTS (PostgreSQL, port 8000) -- NEW
   - Tests run against main.py (root Bio-ERP)
   - Auth endpoint: POST /api/v1/incentivehouse/auth/login
   - Requires PostgreSQL running with bio_erp database
   - Requires SCM staging schema applied (scm_staging_schema.sql)
   - Use: pytest tests/integration/ -v --db-url=postgresql://...

IMPLEMENTATION:
-------------
Create tests/integration/conftest.py:

    import pytest
    from fastapi.testclient import TestClient
    from app.main import app  # Root Bio-ERP app

    @pytest.fixture(scope="module")
    def client():
        return TestClient(app)

    @pytest.fixture(scope="module")
    def auth_token(client):
        # Use root app auth endpoint
        r = client.post("/api/v1/incentivehouse/auth/login", json={
            "username": "test_user",
            "password": "test_pass"
        })
        assert r.status_code == 200
        return r.json()["access_token"]

Create tests/integration/test_scm_bridge_pg.py:

    def test_scm_bridge_events_pg(client, auth_token):
        r = client.get(
            "/api/v1/scm/scm-bridge/production/events",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert r.status_code == 200
        assert "events" in r.json()

RUN ORDER:
----------
1. Start PostgreSQL (or Docker Desktop when available)
2. Run: psql -d bio_erp -f scripts/scm_staging_schema.sql
3. Start root app: uvicorn app.main:app --port 8000
4. Run: pytest tests/integration/ -v

DOCKER WORKAROUND (Docker Desktop unavailable):
---------------------------------------------
If Docker Desktop is unavailable, use local PostgreSQL:
   - Install PostgreSQL 15+ locally
   - Create database: CREATE DATABASE bio_erp;
   - Run DDL: psql -d bio_erp -f scripts/scm_staging_schema.sql
   - Set .env: PRODUCTION_DB_URL=postgresql://postgres:postgres123@localhost:5432/bio_erp
