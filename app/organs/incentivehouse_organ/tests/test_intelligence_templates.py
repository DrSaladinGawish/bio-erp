"""
IHE-ERP v2.4 — Intelligence UI template tests.
Tests for the 3 new dedicated intelligence pages and POST API endpoints.
"""


def test_audit_page_returns_200(sync_client):
    r = sync_client.get("/intelligence/audit")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_or_workbench_page_returns_200(sync_client):
    r = sync_client.get("/intelligence/or")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_scm_workbench_page_returns_200(sync_client):
    r = sync_client.get("/intelligence/scm")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")


def test_audit_page_has_audit_content(sync_client):
    r = sync_client.get("/intelligence/audit")
    assert "Audit" in r.text or "audit" in r.text


def test_or_page_has_engine_cards(sync_client):
    r = sync_client.get("/intelligence/or")
    assert "Linear Programming" in r.text
    assert "EOQ" in r.text or "Economic Order" in r.text


def test_scm_page_has_technique_cards(sync_client):
    r = sync_client.get("/intelligence/scm")
    assert "Value Chain" in r.text or "Strategic Cost" in r.text


def test_or_solve_post_lp_returns_result(sync_client):
    r = sync_client.post(
        "/api/v1/intelligence/or/solve?engine=lp",
        json={"objective": "maximize", "variables": ["x", "y"], "constraints": []},
    )
    assert r.status_code == 200
    data = r.json()
    assert "lp" in data or "engine" in data


def test_scm_analyze_post_returns_result(sync_client):
    r = sync_client.post(
        "/api/v1/intelligence/scm/analyze?cell=value_chain",
        json={"costs": [{"category": "Test", "amount": 100}]},
    )
    assert r.status_code == 200
    data = r.json()
    assert "value_chain" in data or "status" in data


def test_intelligence_breadcrumb_links(sync_client):
    r = sync_client.get("/intelligence/audit")
    assert "/intelligence" in r.text
    assert "Dashboard" in r.text


def test_all_intelligence_pages_extend_base(sync_client):
    for path in ("/intelligence/audit", "/intelligence/or", "/intelligence/scm"):
        r = sync_client.get(path)
        assert r.status_code == 200
        assert "IncentiveHouse" in r.text
