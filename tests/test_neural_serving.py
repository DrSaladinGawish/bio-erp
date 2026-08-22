"""Tests for the checkpoint-loading fix (Gap 1) and API regex fix (Gap 3)."""
import contextlib
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.neural.ann_models import HAS_TORCH
from app.services.neural.ann_predictors import (
    _load_model,
    clear_model_cache,
    get_model_meta,
    predict_churn_ann,
)

pytestmark = pytest.mark.skipif(
    not HAS_TORCH, reason="torch not installed"
)


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_model_cache()
    yield
    clear_model_cache()


# ── GAP 1: trained checkpoints are loaded and deterministic ──────────


class TestCheckpointLoading:
    @pytest.mark.parametrize(
        "name,kwargs",
        [
            ("financial_ann", {"input_size": 128}),
            (
                "revenue_forecaster",
                {
                    "input_size": 4,
                    "hidden_size": 64,
                    "num_layers": 2,
                    "forecast_horizon": 7,
                },
            ),
            ("anomaly_autoencoder", {"input_size": 16, "bottleneck_size": 4}),
        ],
    )
    def test_trained_model_forward_is_deterministic(self, name, kwargs):
        import torch

        model_a = _load_model(name, **kwargs)
        assert model_a is not None, f"{name} checkpoint missing"

        # Same cached object on second call.
        model_b = _load_model(name, **kwargs)
        assert model_b is model_a

        shape = {
            "financial_ann": (1, 128),
            "revenue_forecaster": (1, 30, 4),
            "anomaly_autoencoder": (1, 16),
        }[name]
        x = torch.randn(shape)
        with torch.no_grad():
            out1 = model_a(x)
            out2 = model_a(x)

        if isinstance(out1, dict):
            for k in out1:
                assert torch.equal(out1[k], out2[k])
        elif isinstance(out1, tuple):
            a1, b1 = out1
            a2, b2 = out2
            assert torch.equal(a1, a2) and torch.equal(b1, b2)
        else:
            assert torch.equal(out1, out2)

    def test_loaded_weights_differ_from_fresh_init(self):
        import torch

        from app.services.neural.ann_models import FinancialANN

        served = _load_model("financial_ann", input_size=128)
        fresh = FinancialANN(input_size=128)
        w_served = next(served.parameters())
        w_fresh = next(fresh.parameters())
        assert not torch.equal(w_served, w_fresh), (
            "served weights identical to fresh random init — "
            "checkpoint was NOT loaded"
        )

    def test_demo_trained_client_churn_is_gated_not_silent(self):
        """Checkpoint exists but is demo-trained: it must never claim
        production readiness — meta carries the honest provenance tag
        and serving stamps every response with production_ready=False.
        """
        model = _load_model("client_churn", input_size=8)
        assert model is not None, (
            "demo checkpoint missing — retrain via trainer CLI with "
            "--training-data demo/synthetic"
        )
        meta = get_model_meta("client_churn")
        assert meta.get("training_data") == "demo/synthetic"
        assert meta.get("production_ready") is False


# ── GAP 3: API accepts ANN types, still rejects churn_classifier ─────


@pytest.mark.asyncio
async def test_churn_ann_falls_back_to_heuristic_without_checkpoint(
    monkeypatch,
):
    """Fail-closed: missing checkpoint -> honest heuristic, never random."""
    import app.services.neural.ann_predictors as ann_predictors

    monkeypatch.setattr(
        ann_predictors, "_load_model", lambda *a, **k: None
    )

    class FakeResult:
        def scalar_one_or_none(self):
            return {
                "months_since_last_event": 6,
                "total_events": 10,
                "total_revenue": 5000,
                "avg_event_value": 500,
                "payment_delays": 2,
                "support_tickets": 1,
                "event_frequency_trend": 0.1,
                "revenue_trend": -0.05,
            }

    class FakeSession:
        async def execute(self, *_a, **_k):
            return FakeResult()

    result = await predict_churn_ann(FakeSession(), "X1")
    assert result["method"] == "heuristic"
    assert "churn_probability" in result


@pytest.mark.asyncio
async def test_churn_ann_stamps_demo_provenance():
    """With the demo-trained checkpoint present, serving must use the
    network but stamp training_data=demo/synthetic and flag it as NOT
    production-ready — never silently pass demo output as real.
    """

    class FakeResult:
        def scalar_one_or_none(self):
            return {
                "months_since_last_event": 6,
                "total_events": 10,
                "total_revenue": 5000,
                "avg_event_value": 500,
                "payment_delays": 2,
                "support_tickets": 1,
                "event_frequency_trend": 0.1,
                "revenue_trend": -0.05,
            }

    class FakeSession:
        async def execute(self, *_a, **_k):
            return FakeResult()

    result = await predict_churn_ann(FakeSession(), "X1")
    assert result["method"] == "neural_network"
    assert result["training_data"] == "demo/synthetic"
    assert result["production_ready"] is False



class TestPredictionEndpointHTTP:
    """Real HTTP through the mounted neural router (live Postgres).

    asyncpg pools are event-loop bound, so every test creates its own
    engine and runs seed -> request -> cleanup on a single loop.
    """

    KEY = "__gaptest_fin__"
    KEY_T = "__gaptest_txn__"

    @contextlib.asynccontextmanager
    async def _client(self):
        from httpx import ASGITransport, AsyncClient
        from sqlalchemy import delete
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        from app.config import settings
        from app.database import get_db
        from app.main import app
        from app.middleware.auth import get_current_user
        from app.models.neural.prediction import (
            NeuralFeatureStore,
            NeuralPrediction,
        )

        engine = create_async_engine(settings.DATABASE_URL)
        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        app.dependency_overrides[get_current_user] = lambda: (
            SimpleNamespace(is_superuser=True, is_active=True)
        )

        async def _override_get_db():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = _override_get_db

        try:
            async with factory() as db:
                db.add_all([
                    NeuralFeatureStore(
                        feature_group="financial",
                        feature_key=self.KEY,
                        feature_data={"vector": [0.5] * 128},
                    ),
                    NeuralFeatureStore(
                        feature_group="revenue_history",
                        feature_key=self.KEY,
                        feature_data={
                            "weekly_series": [
                                [0.10, 0.08, 0.30, 0.03]
                                for _ in range(30)
                            ]
                        },
                    ),
                    NeuralFeatureStore(
                        feature_group="transactions",
                        feature_key=self.KEY_T,
                        feature_data={
                            "amount": 5000.0,
                            "debit_amount": 5000.0,
                            "credit_amount": 0.0,
                            "is_reconciled": 0,
                            "txn_type": "CHARGES",
                            "txn_ts": "2026-05-19T14:30:00",
                        },
                    ),
                ])
                await db.commit()

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://localhost",  # TrustedHostMiddleware
            ) as client:
                yield client
        finally:
            async with factory() as db:
                await db.execute(delete(NeuralFeatureStore).where(
                    NeuralFeatureStore.feature_key.in_(
                        [self.KEY, self.KEY_T])
                ))
                await db.execute(delete(NeuralPrediction).where(
                    NeuralPrediction.prediction_key.in_(
                        [self.KEY, self.KEY_T])
                ))
                await db.commit()
            await engine.dispose()
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "ptype,key,expect_field",
        [
            ("financial_ann", KEY, "eva"),
            ("revenue_forecast", KEY, "total_forecast"),
            ("anomaly_detector", KEY_T, "reconstruction_error"),
        ],
    )
    async def test_ann_type_reaches_neural_network_via_http(
        self, ptype, key, expect_field
    ):
        async with self._client() as client:
            resp = await client.post(
                "/api/v1/neural/predict",
                json={"prediction_type": ptype, "entity_id": key},
            )
        assert resp.status_code == 200, resp.text
        body: dict[str, Any] = resp.json()
        assert body["method"] == "neural_network"
        assert expect_field in body

    @pytest.mark.asyncio
    async def test_churn_classifier_still_rejected_by_schema(self):
        async with self._client() as client:
            resp = await client.post(
                "/api/v1/neural/predict",
                json={
                    "prediction_type": "churn_classifier",
                    "entity_id": "x",
                },
            )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_legacy_heuristic_type_still_accepted(self):
        async with self._client() as client:
            resp = await client.post(
                "/api/v1/neural/predict",
                json={
                    "prediction_type": "cash_flow",
                    "entity_id": "__none__",
                },
            )
        assert resp.status_code == 400
