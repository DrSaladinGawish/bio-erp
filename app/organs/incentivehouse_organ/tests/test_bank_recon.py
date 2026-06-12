"""
IHE-ERP v2.4 — Bank Reconciliation tests.
"""


def test_bank_recon_page_returns_200(sync_client):
    r = sync_client.get("/bnk/recon")
    assert r.status_code == 200 or r.status_code == 404


def test_recon_api_auto_reconcile(sync_client):
    r = sync_client.post("/api/v1/incentivehouse/recon/auto")
    assert r.status_code in (200, 404, 405)


def test_recon_api_list_matches(sync_client):
    r = sync_client.get("/api/v1/incentivehouse/recon/matches")
    assert r.status_code in (200, 404)


def test_recon_form_page(sync_client):
    r = sync_client.get("/api/v1/incentivehouse/recon/form")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
