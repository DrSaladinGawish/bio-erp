"""Tests for the AI assist engine (intelligence/ai_assist.py)."""


def test_local_reply_greeting():
    from app.organs.incentivehouse_organ.intelligence.ai_assist import ai_reply

    r = ai_reply("Hello!", "/")
    assert "Hello" in r
    assert "assistant" in r


def test_local_reply_pnr_intent():
    from app.organs.incentivehouse_organ.intelligence.ai_assist import ai_reply

    r = ai_reply("How do I create a new PNR?", "/evn")
    assert "PNR" in r or "Events" in r or "auto-generated" in r


def test_local_reply_sales_intent():
    from app.organs.incentivehouse_organ.intelligence.ai_assist import ai_reply

    r = ai_reply("Create an invoice for a client", "/sal")
    assert "invoice" in r.lower() or "Sales" in r


def test_local_reply_bank_intent():
    from app.organs.incentivehouse_organ.intelligence.ai_assist import ai_reply

    r = ai_reply("How do I reconcile bank transactions?", "/bnk")
    assert "Reconciliation" in r or "bank" in r.lower()


def test_local_reply_empty():
    from app.organs.incentivehouse_organ.intelligence.ai_assist import ai_reply

    r = ai_reply("", "/")
    assert len(r) > 10


def test_local_reply_fallback():
    from app.organs.incentivehouse_organ.intelligence.ai_assist import ai_reply

    r = ai_reply("xyznonexistent12345", "/unknown")
    assert "xyznonexistent12345" in r or len(r) > 10


def test_ai_assist_api_get(sync_client):
    r = sync_client.get("/api/ai/assist")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"


def test_ai_assist_api_post_pnr(sync_client):
    r = sync_client.post(
        "/api/ai/assist",
        json={
            "message": "How do I create a PNR?",
            "page_context": "/evn",
            "current_form_data": {},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "reply" in body
    assert "PNR" in body["reply"] or "Events" in body["reply"]


def test_ai_assist_api_post_greeting(sync_client):
    r = sync_client.post(
        "/api/ai/assist",
        json={
            "message": "Hi there",
            "page_context": "/",
        },
    )
    assert r.status_code == 200
    assert "Hello" in r.json()["reply"]
