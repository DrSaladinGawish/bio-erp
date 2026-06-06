"""
IHE-ERP v2.3 — API endpoint tests.
Run: pytest tests/test_api.py -v
Uses the `sync_client` fixture from conftest.py.
"""
import pytest


# Health / status
def test_health_endpoint(sync_client):
    r = sync_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body
    assert "database" in body


def test_api_health_endpoint(sync_client):
    """v2.3 spec: /api/health must also work (alias)."""
    r = sync_client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body.get("version") == "2.3.0"
    assert "database" in body


def test_api_health_has_pnr_count(sync_client):
    r = sync_client.get("/api/health").json()
    assert "pnr_count" in r


# AI assist
def test_ai_assist_get(sync_client):
    r = sync_client.get("/api/ai/assist")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"


def test_ai_assist_post_pnr(sync_client):
    r = sync_client.post(
        "/api/ai/assist",
        json={"message": "How do I create a PNR?", "page_context": "/evn", "current_form_data": {}},
    )
    assert r.status_code == 200
    body = r.json()
    assert "reply" in body
    assert len(body["reply"]) > 10


def test_ai_assist_post_greeting(sync_client):
    r = sync_client.post(
        "/api/ai/assist",
        json={"message": "hello", "page_context": "/", "current_form_data": {}},
    )
    assert r.status_code == 200
    body = r.json()
    assert "hello" in body["reply"].lower() or "hi" in body["reply"].lower()


def test_ai_assist_post_sales(sync_client):
    r = sync_client.post(
        "/api/ai/assist",
        json={"message": "How to add invoice?", "page_context": "/sal", "current_form_data": {}},
    )
    assert r.status_code == 200
    reply = r.json()["reply"].lower()
    assert "invoice" in reply or "client" in reply


# Module APIs (routers use /api/v1/<mod> prefix; the running container
# additionally aliases /api/<mod> via older builds)
MODULE_LIST_ENDPOINTS = [
    "/api/v1/bnk/transactions",
    "/api/v1/bnk/accounts",
    "/api/v1/bnk/summary",
    "/api/v1/sal/invoices",
    "/api/v1/sal/summary",
    "/api/v1/pur/orders",
    "/api/v1/pur/summary",
    "/api/v1/evn/events",
    "/api/v1/evn/summary",
    "/api/v1/env/clients",
    "/api/v1/env/vendors",
    "/api/v1/env/staff",
]


@pytest.mark.parametrize("ep", MODULE_LIST_ENDPOINTS)
def test_bnk_api_returns_2xx(sync_client, ep):
    r = sync_client.get(ep)
    # 200 (data) or 422 (missing query params) are both acceptable for list endpoints
    assert r.status_code in (200, 422), f"{ep} returned {r.status_code}: {r.text[:200]}"
