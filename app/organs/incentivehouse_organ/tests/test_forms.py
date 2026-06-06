"""
IHE-ERP v2.3 - Form template tests (Path A UI remediation).
Run: pytest tests/test_forms.py -v
"""
import pytest


# Every form page must load successfully
FORM_PAGES = [
    "/evn/new",
    "/sal/new",
    "/pur/new",
    "/bnk/new",
    "/gl/new",
]


@pytest.mark.parametrize("route", FORM_PAGES)
def test_form_page_loads(sync_client, route):
    """Every new-form page must return HTTP 200."""
    r = sync_client.get(route, follow_redirects=False)
    assert r.status_code == 200, f"{route} returned {r.status_code}"


@pytest.mark.parametrize("route", FORM_PAGES)
def test_form_page_is_html(sync_client, route):
    """Form pages must render HTML, not JSON."""
    r = sync_client.get(route)
    assert "text/html" in r.headers.get("content-type", "")


def test_pnr_form_has_required_fields(sync_client):
    r = sync_client.get("/evn/new")
    body = r.text
    for field in ("pnr_number", "client_id", "event_description", "start_date", "end_date"):
        assert field in body, f"PNR form missing field: {field}"


def test_sales_form_has_required_fields(sync_client):
    r = sync_client.get("/sal/new")
    body = r.text
    for field in ("invoice_number", "client_id", "invoice_date", "subtotal"):
        assert field in body, f"Sales form missing field: {field}"


def test_purchases_form_has_required_fields(sync_client):
    r = sync_client.get("/pur/new")
    body = r.text
    for field in ("voucher_number", "vendor_id", "voucher_date", "subtotal"):
        assert field in body, f"Purchases form missing field: {field}"


def test_banking_form_has_required_fields(sync_client):
    r = sync_client.get("/bnk/new")
    body = r.text
    for field in ("transaction_date", "transaction_type", "amount", "description"):
        assert field in body, f"Banking form missing field: {field}"


def test_gl_form_has_required_fields(sync_client):
    r = sync_client.get("/gl/new")
    body = r.text
    for field in ("voucher_date", "voucher_number", "narration"):
        assert field in body, f"GL form missing field: {field}"


# Sidebar should reference every form page (test via a base.html-extending page)
def test_sidebar_references_forms(sync_client):
    r = sync_client.get("/evn")  # evn.html extends base.html
    body = r.text
    for href in ("/evn/new", "/sal/new", "/pur/new", "/bnk/new", "/gl/new"):
        assert href in body, f"Sidebar missing link to {href}"


# Base template should embed AI widget on all pages
def test_ai_widget_on_every_page(sync_client):
    """The AI floating button must be present on pages that extend base.html."""
    # /login is a standalone page (intentional), so excluded
    for path in ("/evn", "/sal", "/pur", "/bnk", "/gl", "/intelligence"):
        r = sync_client.get(path)
        body = r.text
        assert "ai-fab" in body, f"AI widget missing on {path}"
        assert "aiFab" in body, f"AI fab script missing on {path}"


# Real brand images should be referenced
def test_brand_images_referenced(sync_client):
    r = sync_client.get("/evn")  # evn.html extends base.html
    body = r.text
    assert "/static/img/logos.jpg" in body
    assert "/static/img/logosmal.jpg" in body
    assert "/static/img/fotter.jpg" in body
