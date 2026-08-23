"""
ANN Model Tests — Verifies all 4 neural network models in isolation.

Tests:
1. Model instantiation and parameter counting
2. Forward pass with correct output shapes
3. Gradient flow (backward pass)
4. Heuristic fallback helpers
5. Predictor interface compatibility
6. Mini training loop reduces loss
"""

import math
import os
import sys

import pytest

sys.path.insert(0, r"ERP System/BIO_ERP")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp")
os.environ.setdefault("DATABASE_URL_READONLY", "postgresql+asyncpg://bio_erp_reader:DXqF5mW7Hcz4AIg9nSCMFroeyqZegS74thwxuxQVwPQ@localhost:5432/bio_erp")

from app.services.neural.ann_models import (  # noqa: E402
    HAS_TORCH,
    AnomalyAutoencoder,
    ClientChurnClassifier,
    FinancialANN,
    RevenueForecaster,
    count_parameters,
    get_model,
)
from app.services.neural.ann_predictors import (  # noqa: E402
    _anomaly_heuristic,
    _churn_heuristic,
    _extract_feature_vector,
    _financial_heuristic,
    _pad_or_truncate,
    _revenue_heuristic,
    _softmax,
)

requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch unavailable")


# ── Test Group 1: Model Instantiation ────────────────────────────────


def test_torch_available():
    assert HAS_TORCH


@requires_torch
def test_financial_ann_created():
    fin = FinancialANN(input_size=128)
    assert fin is not None
    assert count_parameters(fin) > 10000


@requires_torch
def test_revenue_forecaster_created():
    rev = RevenueForecaster(input_size=4, hidden_size=64, forecast_horizon=7)
    assert rev is not None
    assert count_parameters(rev) > 10000


@requires_torch
def test_anomaly_autoencoder_created():
    ano = AnomalyAutoencoder(input_size=16, bottleneck_size=4)
    assert ano is not None
    assert count_parameters(ano) > 1000


@requires_torch
def test_client_churn_classifier_created():
    chn = ClientChurnClassifier(input_size=8)
    assert chn is not None
    assert count_parameters(chn) > 500


@requires_torch
def test_get_model_factory():
    m = get_model("financial_ann", input_size=128)
    assert m is not None
    with pytest.raises(ValueError):
        get_model("nonexistent_model")


# ── Test Group 2: Forward Pass Shapes ────────────────────────────────


@requires_torch
def test_financial_ann_forward_shapes():
    import torch

    fin = FinancialANN(input_size=128)
    batch = 4
    x_fin = torch.randn(batch, 128)
    out = fin(x_fin)
    assert set(out.keys()) == {"eva", "ebitda", "risk", "bsc"}
    assert out["eva"].shape == (batch, 1)
    assert out["ebitda"].shape == (batch, 1)
    assert out["risk"].shape == (batch, 3)
    assert out["bsc"].shape == (batch, 4)


@requires_torch
def test_revenue_forecaster_forward_shape():
    import torch

    rev = RevenueForecaster(input_size=4, hidden_size=64, forecast_horizon=7)
    batch = 4
    x_rev = torch.randn(batch, 30, 4)
    forecast = rev(x_rev)
    assert forecast.shape == (batch, 7)


@requires_torch
def test_anomaly_autoencoder_forward_shapes():
    import torch

    ano = AnomalyAutoencoder(input_size=16, bottleneck_size=4)
    batch = 4
    x_ano = torch.randn(batch, 16)
    reconstructed, encoded = ano(x_ano)
    assert reconstructed.shape == (batch, 16)
    assert encoded.shape == (batch, 4)


@requires_torch
def test_churn_classifier_forward_shape():
    import torch

    chn = ClientChurnClassifier(input_size=8)
    batch = 4
    x_chn = torch.randn(batch, 8)
    churn = chn(x_chn)
    assert churn.shape == (batch, 1)
    assert churn.min().item() >= 0 and churn.max().item() <= 1


# ── Test Group 3: Gradient Flow ──────────────────────────────────────


@requires_torch
def test_financial_ann_gradients_flow():
    import torch

    fin = FinancialANN(input_size=128)
    x = torch.randn(2, 128, requires_grad=False)
    out = fin(x)
    loss = out["eva"].sum() + out["ebitda"].sum() + out["risk"].sum() + out["bsc"].sum()
    loss.backward()
    grads_ok = all(p.grad is not None for p in fin.parameters() if p.requires_grad)
    assert grads_ok


@requires_torch
def test_revenue_forecaster_gradients_flow():
    import torch

    rev = RevenueForecaster(input_size=4, hidden_size=64, forecast_horizon=7)
    x2 = torch.randn(2, 30, 4)
    forecast = rev(x2)
    forecast.sum().backward()
    grads_ok = all(p.grad is not None for p in rev.parameters() if p.requires_grad)
    assert grads_ok


@requires_torch
def test_anomaly_autoencoder_gradients_flow():
    import torch

    ano = AnomalyAutoencoder(input_size=16, bottleneck_size=4)
    x3 = torch.randn(2, 16)
    recon, _enc = ano(x3)
    ae_loss = ((x3 - recon) ** 2).sum()
    ae_loss.backward()
    grads_ok = all(p.grad is not None for p in ano.parameters() if p.requires_grad)
    assert grads_ok


@requires_torch
def test_churn_classifier_gradients_flow():
    import torch

    chn = ClientChurnClassifier(input_size=8)
    x4 = torch.randn(2, 8)
    churn = chn(x4)
    churn.sum().backward()
    grads_ok = all(p.grad is not None for p in chn.parameters() if p.requires_grad)
    assert grads_ok


# ── Test Group 4: Heuristic Helpers ──────────────────────────────────


def test_financial_heuristic_keys_and_method():
    result = _financial_heuristic(
        {"revenue": 100000, "cost": 60000, "capital_employed": 500000,
         "wacc": 0.10, "da": 10000}
    )
    assert "eva" in result
    assert "ebitda" in result
    assert result["method"] == "heuristic"


def test_revenue_heuristic_forecast_horizon():
    result = _revenue_heuristic(
        {"daily_revenue": [100, 110, 120, 130, 140, 150, 160, 170, 180, 190]}
    )
    assert "forecast" in result
    assert len(result["forecast"]) == 7


def test_anomaly_heuristic_detects_zscore_outlier():
    result = _anomaly_heuristic(
        {"recent_amounts": [1] * 10 + [100]}
    )
    assert "is_anomaly" in result
    assert result["is_anomaly"] is True


def test_churn_heuristic_high_probability_for_inactive_client():
    result = _churn_heuristic({"months_since_last_event": 24, "total_events": 1})
    assert "churn_probability" in result
    assert result["churn_probability"] > 0.5


def test_softmax_sums_to_one():
    sm = _softmax([1.0, 2.0, 3.0])
    assert abs(sum(sm) - 1.0) < 0.001


def test_pad_or_truncate_pads_to_target():
    padded = _pad_or_truncate([1.0, 2.0, 3.0], target_size=5)
    assert len(padded) == 5 and padded[3] == 0.0


def test_extract_feature_vector_returns_list():
    vec = _extract_feature_vector({"a": 1, "b": 2, "c": 3}, expected_size=3)
    assert isinstance(vec, list) and len(vec) == 3


# ── Test Group 5: Predictor Interface Compatibility ──────────────────


def test_predictor_service_registry():
    from app.services.neural.predictor import PredictorService

    assert "financial_ann" in PredictorService.PREDICTORS
    assert "revenue_forecast" in PredictorService.PREDICTORS
    assert "anomaly_detector" in PredictorService.PREDICTORS
    assert "churn_classifier" in PredictorService.PREDICTORS
    assert len(PredictorService.PREDICTORS) == 8


def test_all_predictors_have_predict_method():
    from app.services.neural.predictor import PredictorService

    for name, cls in PredictorService.PREDICTORS.items():
        assert hasattr(cls, "predict") and callable(getattr(cls, "predict")), name


# ── Test Group 6: Mini Training Loop ─────────────────────────────────


@requires_torch
def test_mini_training_loop_reduces_loss():
    import torch

    model = FinancialANN(input_size=128)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
    criterion_mse = torch.nn.MSELoss()
    criterion_ce = torch.nn.CrossEntropyLoss()

    x_fixed = torch.randn(8, 128)
    y_eva = torch.randn(8, 1)
    y_ebitda = torch.randn(8, 1)
    y_risk = torch.randint(0, 3, (8,))
    y_bsc = torch.randn(8, 4)

    initial_loss = None
    for _epoch in range(200):
        out = model(x_fixed)
        loss = (
            criterion_mse(out["eva"], y_eva)
            + criterion_mse(out["ebitda"], y_ebitda)
            + criterion_ce(out["risk"], y_risk)
            + criterion_mse(out["bsc"], y_bsc)
        )
        if initial_loss is None:
            initial_loss = loss.item()
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

    final_loss = loss.item()
    assert final_loss < initial_loss * 0.5
    assert math.isfinite(final_loss)
