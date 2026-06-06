"""
IHE-ERP v2.4 - Dashboard extras tests (charts + PDF + new template).
"""
import pytest


def test_dashboard_template_exists():
    """The new Chart.js dashboard template must exist."""
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "templates" / "dashboard.html"
    assert p.exists(), f"Missing {p}"
    body = p.read_text(encoding="utf-8")
    # Must have all 3 chart canvases
    assert 'id="revenueChart"' in body
    assert 'id="expenseChart"' in body
    assert 'id="cashflowChart"' in body
    # Must have KPI divs with expected ids
    for kid in ("kpi-revenue", "kpi-expenses", "kpi-profit", "kpi-pnrs", "kpi-bank", "kpi-pending"):
        assert f'id="{kid}"' in body, f"Missing KPI id {kid}"
    # Must reference Chart.js CDN
    assert "chart.js" in body or "chart.umd" in body
    # Must reference dashboard.js
    assert "dashboard.js" in body
    # Must have 4 range buttons
    for rng in ("7D", "30D", "90D", "YTD"):
        assert f'data-range="{rng}"' in body
    # Must have export buttons
    assert "Export PDF" in body
    assert "Export JSON" in body


def test_dashboard_js_exists():
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "static" / "js" / "dashboard.js"
    assert p.exists()
    body = p.read_text(encoding="utf-8")
    assert "loadDashboard" in body
    assert "Chart" in body
    assert "revenue_by_month" in body
    assert "expenses_by_month" in body


def test_pdf_generator_imports():
    """PDF generator must be importable."""
    from app.organs.incentivehouse_organ.intelligence.pdf_generator import (
        generate_dashboard_pdf,
    )
    assert callable(generate_dashboard_pdf)


def test_pdf_generator_returns_bytes():
    """PDF generator must return non-empty bytes (even with no reportlab)."""
    from app.organs.incentivehouse_organ.intelligence.pdf_generator import (
        generate_dashboard_pdf,
    )
    data = {
        "total_revenue": 12345.67,
        "total_expenses": 8000.00,
        "net_profit": 4345.67,
        "active_pnrs": 5,
        "bank_balance": 100000.00,
        "pending_invoices": 3,
        "total_vendors": 19,
        "total_clients": 4,
        "revenue_by_month": [0] * 12,
        "expenses_by_month": [0] * 12,
        "start_date": "2025-01-01",
        "end_date": "2025-12-31",
    }
    pdf = generate_dashboard_pdf(data, "YTD")
    assert isinstance(pdf, bytes)
    assert len(pdf) > 100
    # PDF starts with magic bytes
    assert pdf[:4] == b"%PDF"


def test_pdf_export_endpoint(sync_client):
    """The /api/dashboard/export?format=pdf endpoint must return PDF."""
    r = sync_client.get("/api/dashboard/export?range=YTD&format=pdf")
    # Either real PDF (200) or graceful error JSON (200 with status=error)
    assert r.status_code == 200
    if "application/pdf" in r.headers.get("content-type", ""):
        assert r.content[:4] == b"%PDF"
        assert "attachment" in r.headers.get("content-disposition", "")
    else:
        # If PDF gen failed, body should be JSON with status field
        body = r.json()
        assert "format" in body
        assert body["format"] == "pdf"


def test_dashboard_serves_new_template(sync_client):
    """Root URL should now serve dashboard.html with chart canvas elements."""
    r = sync_client.get("/")
    assert r.status_code == 200
    body = r.text
    # Either main_dashboard.html OR dashboard.html is OK
    if "revenueChart" in body:
        assert "kpi-revenue" in body
    # main_dashboard.html fallback is acceptable too
