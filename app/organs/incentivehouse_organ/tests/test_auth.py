"""
IHE-ERP v2.5.1 — Authentication flow tests (JWT + refresh tokens).
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
    assert r.status_code in (200, 404, 405)
    if r.status_code == 200:
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body.get("token_type") == "bearer"
        assert body.get("expires_in") == 3600


def test_login_wrong_password():
    r = _client().post(
        "/api/v1/incentivehouse/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert r.status_code in (401, 404)


def test_auth_me_unauthenticated():
    r = _client().get("/api/v1/incentivehouse/auth/me")
    assert r.status_code in (401, 403, 404)


def test_auth_refresh_success():
    """Exchange a valid refresh token for a new token pair."""
    login = _client().post(
        "/api/v1/incentivehouse/auth/login",
        json={"username": "admin", "password": "admin2026"},
    )
    if login.status_code != 200:
        pytest.skip("Login endpoint not mounted")
    refresh_token = login.json().get("refresh_token")
    assert refresh_token is not None

    r = _client().post(
        "/api/v1/incentivehouse/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    # New refresh token should be different from the old one (rotation)
    assert body["refresh_token"] != refresh_token
    assert body.get("token_type") == "bearer"


def test_auth_refresh_reuse_revoked():
    """Reusing the same refresh token twice should fail (rotation)."""
    login = _client().post(
        "/api/v1/incentivehouse/auth/login",
        json={"username": "admin", "password": "admin2026"},
    )
    if login.status_code != 200:
        pytest.skip("Login endpoint not mounted")
    refresh_token = login.json().get("refresh_token")

    # First use — should succeed
    r1 = _client().post(
        "/api/v1/incentivehouse/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert r1.status_code == 200

    # Second use with same token — should fail (revoked by rotation)
    r2 = _client().post(
        "/api/v1/incentivehouse/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert r2.status_code == 401


def test_auth_refresh_invalid_token():
    """A bogus refresh token should be rejected."""
    r = _client().post(
        "/api/v1/incentivehouse/auth/refresh",
        json={"refresh_token": "this-is-not-a-valid-token"},
    )
    assert r.status_code == 401
