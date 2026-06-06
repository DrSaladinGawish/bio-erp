"""
IHE-ERP v2.3 — Intelligence layer tests.
Run: pytest tests/test_intelligence.py -v
"""
import pytest


INTELLIGENCE_ENDPOINTS = [
    "/api/v1/intelligence/health",
    "/api/v1/intelligence/gap",
    "/api/v1/intelligence/audit",
    "/api/v1/intelligence/backup",
    "/api/v1/intelligence/neural/predict",
    "/api/v1/intelligence/neural/cashflow",
    "/api/v1/intelligence/neural/revenue",
    "/api/v1/intelligence/neural/anomalies",
    "/api/v1/intelligence/or/solve",
    "/api/v1/intelligence/scm/analyze",
]


@pytest.mark.parametrize("ep", INTELLIGENCE_ENDPOINTS)
def test_intelligence_endpoint_returns_2xx(sync_client, ep):
    """Every intelligence endpoint must return 2xx."""
    r = sync_client.get(ep)
    assert 200 <= r.status_code < 300, f"{ep} returned {r.status_code}: {r.text[:200]}"


def test_intelligence_health_shape(sync_client):
    r = sync_client.get("/api/v1/intelligence/health").json()
    assert "db_status" in r
    assert "data_quality_score" in r
    assert "total_records" in r
    assert "table_counts" in r


def test_intelligence_gap_shape(sync_client):
    r = sync_client.get("/api/v1/intelligence/gap").json()
    assert "score" in r
    assert "total_checks" in r
    assert "passed" in r
    assert "failed" in r
    assert "details" in r
    assert isinstance(r["details"], list)
    assert r["total_checks"] >= 20, f"Expected 20+ checks, got {r['total_checks']}"


def test_intelligence_audit_query(sync_client):
    r = sync_client.get("/api/v1/intelligence/audit?limit=5").json()
    assert "items" in r
    assert "count" in r
    assert "total_audit_records" in r
    assert isinstance(r["items"], list)


def test_intelligence_audit_post(sync_client):
    payload = {
        "table_name": "test_table",
        "record_id": "T-1",
        "action": "TEST",
        "user_id": "pytest",
    }
    r = sync_client.post("/api/v1/intelligence/audit", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "error")
    if body["status"] == "ok":
        assert body["id"] > 0


def test_intelligence_backup_list(sync_client):
    r = sync_client.get("/api/v1/intelligence/backup").json()
    assert "backups" in r
    assert isinstance(r["backups"], list)


def test_intelligence_backup_run(sync_client):
    payload = {"reason": "pytest backup", "user_id": "pytest"}
    r = sync_client.post("/api/v1/intelligence/backup", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "status" in body


def test_intelligence_neural_predict(sync_client):
    r = sync_client.get("/api/v1/intelligence/neural/predict").json()
    # All 5 predictors should be present
    assert "cashflow" in r
    assert "revenue" in r
    assert "anomaly" in r
    assert "client_score" in r
    assert "vendor_rank" in r


def test_intelligence_or_solve_all(sync_client):
    r = sync_client.get("/api/v1/intelligence/or/solve?engine=all").json()
    # All 6 engines
    for eng in ("lp", "eoq", "pert", "profit", "breakeven", "forecast"):
        assert eng in r, f"Missing OR engine: {eng}"


def test_intelligence_or_solve_single(sync_client):
    r = sync_client.get("/api/v1/intelligence/or/solve?engine=eoq").json()
    assert "eoq" in r


def test_intelligence_scm_analyze(sync_client):
    r = sync_client.get("/api/v1/intelligence/scm/analyze?cell=all").json()
    assert "value_chain" in r
    assert "strategic_cost" in r
    assert "sustainability" in r


def test_intelligence_page(sync_client):
    """The /intelligence HTML page must load."""
    r = sync_client.get("/intelligence")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
