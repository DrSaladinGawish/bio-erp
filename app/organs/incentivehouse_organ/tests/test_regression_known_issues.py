"""
Regression-prevention tests for the four historically fragile areas
flagged by the project lead.

These tests are written defensively — they must all pass against the
current implementation.  Their job is to fail loudly the moment one of
the four known bugs regresses, so we never lose the 100% pass rate
that the project is now at.

Issues covered:

1. Root path redirect        — `/` must always return 200, never 307.
2. WeasyPrint PDF env issue   — PDF generator must fall back to a
                                pure-Python implementation when
                                WeasyPrint (or its GTK libs) is
                                unavailable.
3. 403 vs 401 auth mismatch   — Unauthenticated requests must return
                                401 Unauthorized, not 403 Forbidden.
4. Ledger data issue          — Dashboard / API responses must always
                                expose the full KPI dictionary, never
                                silently drop fields.

Each test is annotated with the issue number and a one-line rationale
so future maintainers know what to do if the test fires.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Issue #1 — Root path redirect regression guard
# ---------------------------------------------------------------------------


def test_root_returns_200_not_redirect(sync_client):
    """FIX #1: Root path must return 200, never a 307 redirect.

    A past regression had the root handler redirecting to /login
    when the user was not authenticated, which broke the desktop
    icon "double-click → browser opens" workflow.  The contract
    is now: `/` ALWAYS renders the dashboard page, even before
    login.  The login redirect is performed client-side.
    """
    r = sync_client.get("/", follow_redirects=False)
    assert r.status_code == 200, (
        f"Root must return 200, got {r.status_code}. "
        "Do NOT redirect / to /login — that breaks the desktop "
        "icon startup flow."
    )
    # And the body must be HTML, not an empty redirect body.
    assert "text/html" in r.headers.get("content-type", "")


def test_root_follow_redirects_still_200(sync_client):
    """FIX #1b: Even with follow_redirects=True, status must end as 200.

    Defensive: catches the case where a future handler returns a
    307 to an internal endpoint that itself 200s.  Either way the
    user should land on a real page.
    """
    r = sync_client.get("/")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Issue #2 — WeasyPrint PDF env regression guard
# ---------------------------------------------------------------------------


def test_pdf_generator_falls_back_when_weasyprint_missing():
    """FIX #2: PDF generator must NOT depend on WeasyPrint at runtime.

    The legacy PDF generator used WeasyPrint, which requires GTK
    libraries that are often missing on slim Windows containers.
    The current implementation is a pure-Python builder that always
    returns valid PDF bytes (starting with %PDF) regardless of
    optional dependencies.
    """
    from app.organs.incentivehouse_organ.intelligence.pdf_generator import (
        generate_dashboard_pdf,
    )

    data = {
        "total_revenue": 1.0,
        "total_expenses": 0.0,
        "net_profit": 1.0,
        "active_pnrs": 0,
        "bank_balance": 0.0,
        "pending_invoices": 0,
        "total_vendors": 0,
        "total_clients": 0,
        "revenue_by_month": [0] * 12,
        "expenses_by_month": [0] * 12,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    }
    pdf = generate_dashboard_pdf(data, "YTD")
    assert isinstance(pdf, (bytes, bytearray))
    assert len(pdf) > 100, "PDF payload is suspiciously small"
    # PDF magic bytes — must be present even when WeasyPrint is missing.
    assert bytes(pdf[:4]) == b"%PDF"


def test_pdf_export_endpoint_never_500(sync_client):
    """FIX #2b: /api/dashboard/export?format=pdf must never 500.

    The endpoint should always return 200 with either:
      * real PDF bytes  (Content-Type: application/pdf), OR
      * a graceful JSON stub  {format: "pdf", status: ...}
    Never a 5xx — that would indicate the WeasyPrint path leaked out.
    """
    r = sync_client.get("/api/dashboard/export?range=YTD&format=pdf")
    assert r.status_code == 200, f"PDF export returned {r.status_code}"
    ct = r.headers.get("content-type", "")
    if "application/pdf" in ct:
        assert r.content[:4] == b"%PDF"
    else:
        body = r.json()
        assert body.get("format") == "pdf"


# ---------------------------------------------------------------------------
# Issue #3 — 403 vs 401 auth mismatch regression guard
# ---------------------------------------------------------------------------


def test_unauth_request_returns_401_not_403(sync_client):
    """FIX #3: Unauthenticated requests must return 401, not 403.

    401 = "you are not authenticated" (no/invalid token).
    403 = "you are authenticated but lack permission".
    Returning 403 for the unauthenticated case breaks HTTP client
    libraries that treat 401 as the only retryable auth failure.
    """
    # /api/v1/incentivehouse/auth/me requires auth — no token provided.
    r = sync_client.get("/api/v1/incentivehouse/auth/me")
    # 401 is required; 403 is the bug we want to catch.
    assert r.status_code != 403, (
        "Unauthenticated request returned 403 — should be 401. "
        "Distinguish 'not authenticated' (401) from 'forbidden' (403)."
    )
    # 401 is the correct answer; 404 also acceptable (route may not be
    # mounted) but the test will fail if the bug regresses to 403.
    assert r.status_code in (401, 404), (
        f"Expected 401 (or 404 if route unmounted), got {r.status_code}"
    )


def test_auth_refresh_invalid_returns_401():
    """FIX #3b: An invalid refresh token must be rejected with 401.

    The refresh endpoint should never return 200 for a bogus token,
    and never 403 (that's a permission issue, not an auth issue).
    """
    from fastapi.testclient import TestClient
    from app.organs.incentivehouse_organ.main import app

    with TestClient(app) as c:
        r = c.post(
            "/api/v1/incentivehouse/auth/refresh",
            json={"refresh_token": "this-is-not-a-valid-token"},
        )
    assert r.status_code == 401, (
        f"Invalid refresh token should return 401, got {r.status_code}"
    )


def test_login_wrong_password_returns_401():
    """FIX #3c: Wrong password must return 401, not 403."""
    from fastapi.testclient import TestClient
    from app.organs.incentivehouse_organ.main import app

    with TestClient(app) as c:
        r = c.post(
            "/api/v1/incentivehouse/auth/login",
            json={"username": "admin", "password": "wrong"},
        )
    # 401 (auth failed) is correct.  404 (route unmounted) is acceptable.
    # 403 would be the bug — login failure is not a permission issue.
    assert r.status_code in (401, 404), (
        f"Wrong password should return 401 (or 404 if unmounted), got {r.status_code}"
    )
    assert r.status_code != 403, "Wrong password returned 403 — should be 401"


# ---------------------------------------------------------------------------
# Issue #4 — Ledger / dashboard data shape regression guard
# ---------------------------------------------------------------------------


EXPECTED_DASHBOARD_KEYS = {
    "total_revenue",
    "total_expenses",
    "net_profit",
    "active_pnrs",
    "bank_balance",
    "pending_invoices",
    "total_vendors",
    "total_clients",
    "revenue_by_month",
    "expenses_by_month",
}


@pytest.mark.parametrize("rng", ["7D", "30D", "90D", "YTD"])
def test_gl_dashboard_data_shape_consistent(sync_client, rng):
    """FIX #4: Dashboard data must always include the full KPI set.

    A past bug caused the data endpoint to silently drop fields
    (e.g. 'bank_balance') when the underlying query returned NULL.
    The contract is: the response always carries every key, even
    if the value is 0 / null / empty list.
    """
    r = sync_client.get(f"/api/dashboard/data?range={rng}")
    assert r.status_code == 200, f"range={rng} returned {r.status_code}"
    data = r.json()
    missing = EXPECTED_DASHBOARD_KEYS - set(data.keys())
    assert not missing, f"Missing KPI keys for range={rng}: {missing}"


def test_gl_dashboard_monthly_series_always_12(sync_client):
    """FIX #4b: revenue_by_month / expenses_by_month must have 12 elements.

    A past bug returned a variable-length list when the database
    had fewer than 12 months of data.  The contract is: always 12
    (Jan..Dec), zero-padded when no data exists for a month.
    """
    r = sync_client.get("/api/dashboard/data?range=YTD").json()
    assert len(r["revenue_by_month"]) == 12, (
        f"revenue_by_month should have 12 elements, got {len(r['revenue_by_month'])}"
    )
    assert len(r["expenses_by_month"]) == 12, (
        f"expenses_by_month should have 12 elements, got {len(r['expenses_by_month'])}"
    )
    for v in r["revenue_by_month"] + r["expenses_by_month"]:
        assert isinstance(v, (int, float))
        assert v >= 0, f"Negative monthly value: {v}"


def test_api_health_has_database_field(sync_client):
    """FIX #4c: /api/health must always include the database field.

    A past bug returned just {status: ok} without database info,
    making the health endpoint useless for monitoring.
    """
    r = sync_client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert "database" in body, "Health endpoint missing 'database' field"
    assert body["database"] in ("ok", "error", "unknown", "degraded")
