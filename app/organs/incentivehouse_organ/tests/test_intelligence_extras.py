"""
IHE-ERP v2.4 — Additional intelligence layer edge case and integration tests.
"""


def test_audit_post_and_query_back(sync_client):
    payload = {
        "table_name": "test_edge",
        "record_id": "EDGE-001",
        "action": "TEST",
        "user_id": "pytest_edge",
    }
    r = sync_client.post("/api/v1/intelligence/audit", json=payload)
    assert r.status_code == 200
    post_body = r.json()
    if post_body.get("status") == "ok":
        q = sync_client.get(
            "/api/v1/intelligence/audit?table_name=test_edge&limit=10"
        ).json()
        assert q["count"] > 0
        assert any(i["table_name"] == "test_edge" for i in q["items"])


def test_audit_export_endpoint(sync_client):
    r = sync_client.get("/api/v1/intelligence/audit?limit=500")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert len(data["items"]) <= 500


def test_gap_analysis_check_count(sync_client):
    r = sync_client.get("/api/v1/intelligence/gap").json()
    assert r["total_checks"] >= 20
    assert r["passed"] + r["failed"] == r["total_checks"]


def test_or_solve_eoq(sync_client):
    r = sync_client.get("/api/v1/intelligence/or/solve?engine=eoq").json()
    assert "eoq" in r
    assert r["eoq"]["status"] == "ok"
    assert r["eoq"]["eoq"] > 0


def test_or_solve_breakeven(sync_client):
    r = sync_client.get("/api/v1/intelligence/or/solve?engine=breakeven").json()
    assert "breakeven" in r
    assert r["breakeven"]["status"] == "ok"
    assert r["breakeven"]["breakeven_units"] > 0


def test_scm_sustainability(sync_client):
    r = sync_client.get("/api/v1/intelligence/scm/analyze?cell=sustainability").json()
    assert "sustainability" in r
    assert "grade" in r["sustainability"]
    assert r["sustainability"]["grade"] in ("A", "B", "C", "D")


def test_neural_cashflow_shape(sync_client):
    r = sync_client.get("/api/v1/intelligence/neural/cashflow").json()
    assert "predictor" in r
    assert "forecast" in r
    assert "total_forecast" in r


def test_neural_anomalies_shape(sync_client):
    r = sync_client.get("/api/v1/intelligence/neural/anomalies").json()
    assert "predictor" in r
    assert "anomalies" in r


def test_neural_revenue_shape(sync_client):
    r = sync_client.get("/api/v1/intelligence/neural/revenue").json()
    assert "predictor" in r
    assert "forecast" in r
    assert "total_forecast" in r


def test_health_db_status(sync_client):
    r = sync_client.get("/api/v1/intelligence/health").json()
    assert r["db_status"] in ("ok", "error", "unknown")


def test_backup_list_returns_list(sync_client):
    r = sync_client.get("/api/v1/intelligence/backup").json()
    assert isinstance(r["backups"], list)


def test_backup_run_returns_status(sync_client):
    r = sync_client.post(
        "/api/v1/intelligence/backup",
        json={"reason": "pytest edge test", "user_id": "pytest"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "skipped", "error")


def test_or_solve_all_engines_present(sync_client):
    r = sync_client.get("/api/v1/intelligence/or/solve?engine=all").json()
    for eng in ("lp", "eoq", "pert", "profit", "breakeven", "forecast"):
        assert eng in r, f"Missing engine: {eng}"
        assert "status" in r[eng]


def test_dashboard_kpis_not_hardcoded(sync_client):
    r = sync_client.get("/api/dashboard/data?range=YTD").json()
    assert "4,769,491" not in str(r)


def test_dashboard_data_typecheck(sync_client):
    r = sync_client.get("/api/dashboard/data?range=7D").json()
    for key in ("total_revenue", "total_expenses", "net_profit", "bank_balance"):
        assert isinstance(r[key], (int, float)), f"{key} not numeric"
    assert isinstance(r["active_pnrs"], int)
    assert isinstance(r["pending_invoices"], int)


def test_scm_all_cells_present(sync_client):
    r = sync_client.get("/api/v1/intelligence/scm/analyze?cell=all").json()
    for cell in ("value_chain", "strategic_cost", "sustainability"):
        assert cell in r, f"Missing cell: {cell}"
