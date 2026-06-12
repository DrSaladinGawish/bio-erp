import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.usefixtures("db_session")

BASE = "/api/v1/neural"

SAMPLE_PREDICTION = {
    "prediction_type": "cash_flow",
    "prediction_key": "test_entity_001",
    "predicted_value": 15000.50,
    "confidence": 0.85,
    "model_version": "1.0.0",
}

SAMPLE_FEATURE = {
    "feature_group": "cash_flow",
    "feature_key": "test_entity_001",
    "feature_data": {
        "avg_monthly_inflow": 50000,
        "avg_monthly_outflow": 35000,
        "current_balance": 100000,
        "growth_rate": 0.05,
    },
}

SAMPLE_MEMORY = {
    "memory_type": "insight",
    "memory_key": "test_insight_001",
    "content": "Test neural memory content",
    "importance": 0.7,
}


class TestNeuralAuth:
    async def test_no_auth_returns_401(self, client: AsyncClient):
        resp = await client.get(f"{BASE}/predictions")
        assert resp.status_code in (401, 403)

    async def test_no_auth_post_returns_401(self, client: AsyncClient):
        resp = await client.post(f"{BASE}/predictions", json=SAMPLE_PREDICTION)
        assert resp.status_code in (401, 403)


class TestPredictions:
    async def test_create_prediction_returns_201(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            f"{BASE}/predictions", json=SAMPLE_PREDICTION, headers=auth_headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["prediction_type"] == "cash_flow"
        assert body["predicted_value"] == 15000.50
        assert "id" in body

    async def test_list_predictions_returns_200(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(
            f"{BASE}/predictions", json=SAMPLE_PREDICTION, headers=auth_headers
        )
        resp = await client.get(f"{BASE}/predictions", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["data"]) >= 1

    async def test_get_prediction_returns_200(
        self, client: AsyncClient, auth_headers: dict
    ):
        create = await client.post(
            f"{BASE}/predictions", json=SAMPLE_PREDICTION, headers=auth_headers
        )
        pid = create.json()["id"]
        resp = await client.get(f"{BASE}/predictions/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == pid

    async def test_get_prediction_not_found_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.get(f"{BASE}/predictions/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_filter_by_prediction_type(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(
            f"{BASE}/predictions", json=SAMPLE_PREDICTION, headers=auth_headers
        )
        resp = await client.get(
            f"{BASE}/predictions?prediction_type=cash_flow", headers=auth_headers
        )
        assert resp.status_code == 200
        for item in resp.json()["data"]:
            assert item["prediction_type"] == "cash_flow"

    async def test_invalid_prediction_type_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        bad = {**SAMPLE_PREDICTION, "prediction_type": "invalid_type"}
        resp = await client.post(f"{BASE}/predictions", json=bad, headers=auth_headers)
        assert resp.status_code == 422

    async def test_prediction_type_enum_validation(
        self, client: AsyncClient, auth_headers: dict
    ):
        for ptype in [
            "cash_flow",
            "client_churn",
            "pnr_overrun",
            "transaction_anomaly",
        ]:
            payload = {**SAMPLE_PREDICTION, "prediction_type": ptype}
            resp = await client.post(
                f"{BASE}/predictions", json=payload, headers=auth_headers
            )
            assert resp.status_code == 201, f"Failed for type {ptype}"


class TestPredictEndpoint:
    async def test_predict_no_features_returns_400(
        self, client: AsyncClient, auth_headers: dict
    ):
        req = {"prediction_type": "cash_flow", "entity_id": "nonexistent"}
        resp = await client.post(f"{BASE}/predict", json=req, headers=auth_headers)
        assert resp.status_code == 400

    async def test_predict_with_features_returns_prediction(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(f"{BASE}/features", json=SAMPLE_FEATURE, headers=auth_headers)
        req = {"prediction_type": "cash_flow", "entity_id": "test_entity_001"}
        resp = await client.post(f"{BASE}/predict", json=req, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "predicted_value" in body
        assert "confidence" in body
        assert body["predicted_value"] > 0

    async def test_unknown_prediction_type_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        req = {"prediction_type": "unknown_type", "entity_id": "test"}
        resp = await client.post(f"{BASE}/predict", json=req, headers=auth_headers)
        assert resp.status_code == 422


class TestFeedback:
    async def test_submit_feedback_returns_200(
        self, client: AsyncClient, auth_headers: dict
    ):
        create = await client.post(
            f"{BASE}/predictions", json=SAMPLE_PREDICTION, headers=auth_headers
        )
        pid = create.json()["id"]
        resp = await client.post(
            f"{BASE}/predictions/{pid}/feedback",
            json={"prediction_id": pid, "actual_value": 16000.0},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_feedback_not_found_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            f"{BASE}/predictions/99999/feedback",
            json={"prediction_id": 99999, "actual_value": 100.0},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestFeatures:
    async def test_create_feature_returns_201(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            f"{BASE}/features", json=SAMPLE_FEATURE, headers=auth_headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["feature_group"] == "cash_flow"
        assert body["feature_data"]["avg_monthly_inflow"] == 50000

    async def test_list_features_returns_200(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(f"{BASE}/features", json=SAMPLE_FEATURE, headers=auth_headers)
        resp = await client.get(f"{BASE}/features", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_filter_features_by_group(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(f"{BASE}/features", json=SAMPLE_FEATURE, headers=auth_headers)
        resp = await client.get(
            f"{BASE}/features?feature_group=cash_flow", headers=auth_headers
        )
        assert resp.status_code == 200
        for item in resp.json():
            assert item["feature_group"] == "cash_flow"


class TestTraining:
    async def test_create_training_returns_201(
        self, client: AsyncClient, auth_headers: dict
    ):
        payload = {
            "model_name": "test_model",
            "dataset_size": 1000,
            "parameters": {"lr": 0.01},
        }
        resp = await client.post(f"{BASE}/training", json=payload, headers=auth_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["model_name"] == "test_model"
        assert body["training_status"] == "pending"

    async def test_list_training_returns_200(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(
            f"{BASE}/training", json={"model_name": "m1"}, headers=auth_headers
        )
        resp = await client.get(f"{BASE}/training", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_filter_training_by_model_name(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(
            f"{BASE}/training", json={"model_name": "filter_me"}, headers=auth_headers
        )
        resp = await client.get(
            f"{BASE}/training?model_name=filter_me", headers=auth_headers
        )
        assert resp.status_code == 200
        for item in resp.json():
            assert item["model_name"] == "filter_me"


class TestMemory:
    async def test_create_memory_returns_201(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.post(
            f"{BASE}/memory", json=SAMPLE_MEMORY, headers=auth_headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["memory_type"] == "insight"
        assert body["content"] == "Test neural memory content"

    async def test_list_memory_returns_200(
        self, client: AsyncClient, auth_headers: dict
    ):
        await client.post(f"{BASE}/memory", json=SAMPLE_MEMORY, headers=auth_headers)
        resp = await client.get(f"{BASE}/memory", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_filter_memory_by_type(self, client: AsyncClient, auth_headers: dict):
        await client.post(f"{BASE}/memory", json=SAMPLE_MEMORY, headers=auth_headers)
        resp = await client.get(
            f"{BASE}/memory?memory_type=insight", headers=auth_headers
        )
        for item in resp.json():
            assert item["memory_type"] == "insight"

    async def test_delete_memory_returns_204(
        self, client: AsyncClient, auth_headers: dict
    ):
        create = await client.post(
            f"{BASE}/memory", json=SAMPLE_MEMORY, headers=auth_headers
        )
        mid = create.json()["id"]
        resp = await client.delete(f"{BASE}/memory/{mid}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_delete_memory_not_found_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        resp = await client.delete(f"{BASE}/memory/99999", headers=auth_headers)
        assert resp.status_code == 404

    async def test_invalid_memory_type_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        bad = {**SAMPLE_MEMORY, "memory_type": "invalid"}
        resp = await client.post(f"{BASE}/memory", json=bad, headers=auth_headers)
        assert resp.status_code == 422


class TestDashboard:
    async def test_dashboard_returns_200(self, client: AsyncClient, auth_headers: dict):
        await client.post(
            f"{BASE}/predictions", json=SAMPLE_PREDICTION, headers=auth_headers
        )
        await client.post(f"{BASE}/memory", json=SAMPLE_MEMORY, headers=auth_headers)
        resp = await client.get(f"{BASE}/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "total_predictions" in body
        assert "by_type" in body
        assert "active_memories" in body
        assert body["total_predictions"] >= 1


ENDPOINTS = [
    ("GET", f"{BASE}/predictions"),
    ("GET", f"{BASE}/features"),
    ("GET", f"{BASE}/training"),
    ("GET", f"{BASE}/memory"),
    ("GET", f"{BASE}/dashboard"),
]


@pytest.mark.parametrize("method,path", ENDPOINTS)
async def test_neural_endpoints_not_500(
    method: str, path: str, client: AsyncClient, auth_headers: dict
):
    resp = await client.request(method, path, headers=auth_headers)
    assert resp.status_code < 500
