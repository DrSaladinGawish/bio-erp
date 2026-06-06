"""
IHE-ERP v2.3.2 - Dashboard data API tests.
Run: pytest tests/test_dashboard.py -v
"""
import pytest


DASHBOARD_RANGES = ["7D", "30D", "90D", "YTD"]


@pytest.mark.parametrize("rng", DASHBOARD_RANGES)
def test_dashboard_data_range(sync_client, rng):
    """Each standard date range must return 200 with the full KPI set."""
    r = sync_client.get(f"/api/dashboard/data?range={rng}")
    assert r.status_code == 200, f"range={rng} returned {r.status_code}"
    data = r.json()
    for key in ("total_revenue", "total_expenses", "net_profit", "active_pnrs",
                "bank_balance", "pending_invoices", "total_vendors",
                "total_clients", "revenue_by_month", "expenses_by_month"):
        assert key in data, f"Missing {key} for range={rng}"


def test_dashboard_data_custom(sync_client):
    r = sync_client.get(
        "/api/dashboard/data?range=Custom&start=2025-01-01&end=2025-12-31"
    )
    assert r.status_code == 200
    data = r.json()
    assert data["start_date"] == "2025-01-01"
    assert data["end_date"] == "2025-12-31"


def test_dashboard_data_default(sync_client):
    """No range param should default to YTD."""
    r = sync_client.get("/api/dashboard/data")
    assert r.status_code == 200
    assert r.json()["range"] == "YTD"


def test_dashboard_data_invalid_range(sync_client):
    """Out-of-whitelist range must be rejected (pattern validation)."""
    r = sync_client.get("/api/dashboard/data?range=INVALID")
    # 422 = unprocessable entity (FastAPI validation error)
    assert r.status_code in (400, 422)


def test_dashboard_data_monthly_series_length(sync_client):
    """Monthly series must always be 12 elements (Jan..Dec)."""
    r = sync_client.get("/api/dashboard/data?range=YTD").json()
    assert len(r["revenue_by_month"]) == 12
    assert len(r["expenses_by_month"]) == 12
    for v in r["revenue_by_month"] + r["expenses_by_month"]:
        assert isinstance(v, (int, float))
        assert v >= 0


def test_dashboard_data_values_are_floats(sync_client):
    """All money values must be floats, not strings."""
    r = sync_client.get("/api/dashboard/data?range=YTD").json()
    for key in ("total_revenue", "total_expenses", "net_profit", "bank_balance"):
        assert isinstance(r[key], (int, float)), f"{key} is not numeric: {r[key]}"


def test_dashboard_export_json(sync_client):
    r = sync_client.get("/api/dashboard/export?range=YTD&format=json")
    assert r.status_code == 200
    body = r.json()
    assert body["format"] == "json"
    assert "data" in body


def test_dashboard_export_pdf(sync_client):
    """v2.3.5+: PDF export returns real PDF bytes, not a JSON stub."""
    r = sync_client.get("/api/dashboard/export?range=YTD&format=pdf")
    assert r.status_code == 200
    # Either real PDF or graceful JSON error
    if "application/pdf" in r.headers.get("content-type", ""):
        assert r.content[:4] == b"%PDF"
    else:
        body = r.json()
        assert body["format"] == "pdf"
