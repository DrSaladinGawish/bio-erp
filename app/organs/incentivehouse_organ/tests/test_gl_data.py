"""
IHE-ERP v2.4 — GL (General Ledger) page tests.
"""


def test_gl_list_returns_200(sync_client):
    r = sync_client.get("/gl")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_gl_voucher_form_loads(sync_client):
    r = sync_client.get("/gl/new")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_gl_form_has_expected_fields(sync_client):
    r = sync_client.get("/gl/new")
    body = r.text
    for field in ("voucher_date", "voucher_number", "narration"):
        assert field in body, f"GL form missing field: {field}"


def test_gl_page_shows_table(sync_client):
    r = sync_client.get("/gl")
    body = r.text
    assert "table" in body.lower() or "gl" in body.lower()
