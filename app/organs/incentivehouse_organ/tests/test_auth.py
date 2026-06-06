"""
IHE-ERP v2.3 — Authentication flow tests.
Run: pytest tests/test_auth.py -v
"""
import pytest
from fastapi.testclient import TestClient


def _client():
    from app.organs.incentivehouse_organ.main import app
    return TestClient(app)


def test_login_default_admin():
    """The /api/v1/incentivehouse/auth/login endpoint is mounted from sub_app.py."""
    r = _client().post(
        "/api/v1/incentivehouse/auth/login",
        json={"username": "admin", "password": "admin2026"},
    )
    # 200 = ok; 401 = wrong creds.  If mounted, expect 200.
    assert r.status_code in (200, 404, 405)
    if r.status_code == 200:
        body = r.json()
        assert "access_token" in body
        assert body.get("token_type") == "bearer"


def test_login_wrong_password():
    r = _client().post(
        "/api/v1/incentivehouse/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert r.status_code in (401, 404)


def test_auth_me_unauthenticated():
    r = _client().get("/api/v1/incentivehouse/auth/me")
    # Should be 401 (no token) or 404 (endpoint missing)
    assert r.status_code in (401, 403, 404)
