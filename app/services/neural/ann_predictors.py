"""
ANN-Backed Predictors — Real neural network predictors that plug into
the existing PredictorService interface.

Each predictor:
1. Fetches features from NeuralFeatureStore (same as heuristic predictors)
2. Runs inference through a real PyTorch model
3. Returns results in the same format as heuristic predictors
4. Falls back to heuristic methods if torch is unavailable or model not loaded
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.neural.prediction import NeuralFeatureStore

logger = logging.getLogger(__name__)

try:
    import torch

    from app.services.neural.ann_models import (
        HAS_TORCH,
        WEEKLY_MONEY_SCALE,
        AnomalyAutoencoder,
        ClientChurnClassifier,
        FinancialANN,
        RevenueForecaster,
        build_txn_vector,
        count_parameters,
        get_model,
    )
except ImportError:
    HAS_TORCH = False
    logger.warning("torch unavailable — ANN predictors will use heuristic fallback")


REVENUE_LOOKBACK_WEEKS = 30


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ── Model Registry (loaded once, reused) ─────────────────────────────

# Same layout trainer.py writes to: trained_models/<name>.pt
MODELS_DIR = Path(__file__).resolve().parents[3] / "trained_models"

_model_cache: dict[str, Any] = {}
_model_meta: dict[str, dict[str, Any]] = {}


def get_model_meta(model_name: str) -> dict[str, Any]:
    """Training provenance of the loaded checkpoint (empty if not loaded)."""
    return _model_meta.get(model_name, {})


def _load_model(model_name: str, **kwargs: Any) -> Any:
    """
    Load a TRAINED model from its checkpoint, cached across requests.

    Fail-closed contract: if the checkpoint is missing or cannot be
    loaded strictly, return None so callers fall back to the honest
    heuristic path. Never serve randomly-initialized weights.
    """
    if model_name in _model_cache:
        return _model_cache[model_name]
    if not HAS_TORCH:
        return None

    ckpt_path = MODELS_DIR / f"{model_name}.pt"
    if not ckpt_path.exists():
        logger.warning(
            "No trained checkpoint for %r at %s — refusing "
            "random-weight inference; caller will use heuristic.",
            model_name,
            ckpt_path,
        )
        return None

    try:
        model = get_model(model_name, **kwargs)
        checkpoint = torch.load(
            ckpt_path, map_location="cpu", weights_only=True
        )
        model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    except Exception as exc:  # noqa: BLE001 — must never serve random weights
        logger.error(
            "Checkpoint load failed for %r (%s): %s",
            model_name,
            ckpt_path,
            exc,
        )
        return None

    model.eval()
    _model_cache[model_name] = model
    _model_meta[model_name] = {
        "training_data": checkpoint.get("training_data", "unknown"),
        "trained_at": checkpoint.get("trained_at"),
        "epochs": checkpoint.get("epochs"),
        "threshold": checkpoint.get("threshold"),
    }
    _model_meta[model_name]["production_ready"] = (
        _model_meta[model_name]["training_data"] == "real"
    )
    if not _model_meta[model_name]["production_ready"]:
        logger.warning(
            "Checkpoint %s is trained on %r data — NOT production "
            "grade; consumers must surface this provenance.",
            ckpt_path.name,
            _model_meta[model_name]["training_data"],
        )
    logger.info(
        "Loaded trained checkpoint %s (epochs=%s)",
        ckpt_path.name,
        checkpoint.get("epochs"),
    )
    return model


def _stamp_provenance(result: dict[str, Any], model_name: str) -> dict[str, Any]:
    """
    Attach training-data provenance to an ANN-path result so no
    consumer can mistake a demo/unknown-provenance prediction for a
    production-grade one.
    """
    meta = get_model_meta(model_name)
    result["training_data"] = meta.get("training_data", "unknown")
    result["production_ready"] = result["training_data"] == "real"
    return result


def clear_model_cache() -> None:
    """Clear cached models (useful for testing)."""
    _model_cache.clear()


# ── Financial ANN Predictor ──────────────────────────────────────────


async def predict_financial_ann(
    db: AsyncSession,
    entity_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Predict EVA, EBITDA, risk classification, and BSC scores using
    a real feedforward neural network.

    Falls back to linear heuristic if torch is unavailable.
    """
    features = await _fetch_features(db, "financial", entity_id)
    if not features:
        return {"error": f"No financial features found for entity {entity_id}"}

    feature_vector = _extract_feature_vector(features, expected_size=128)

    if HAS_TORCH and feature_vector is not None:
        model = _load_model("financial_ann", input_size=len(feature_vector))
        if model is not None:
            try:
                with torch.no_grad():
                    x = torch.tensor([feature_vector], dtype=torch.float32)
                    outputs = model(x)
                return _stamp_provenance({
                    "method": "neural_network",
                    "model": "FinancialANN",
                    "parameters": count_parameters(model),
                    "eva": round(outputs["eva"].item(), 2),
                    "ebitda": round(outputs["ebitda"].item(), 2),
                    "risk_class": _softmax(outputs["risk"].tolist()[0]),
                    "bsc_scores": _softmax(outputs["bsc"].tolist()[0]),
                    "confidence": 0.85,
                }, "financial_ann")
            except Exception as e:
                logger.warning("FinancialANN inference failed, falling back: %s", e)

    return _financial_heuristic(features)


# ── Revenue Forecaster (LSTM) ────────────────────────────────────────


async def predict_revenue_ann(
    db: AsyncSession,
    entity_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Forecast 7-day revenue using LSTM time-series model.

    Falls back to linear regression if torch is unavailable.
    """
    features = await _fetch_features(db, "revenue_history", entity_id)
    if not features:
        return {"error": f"No revenue history found for entity {entity_id}"}

    if HAS_TORCH and "weekly_series" in features:
        model = _load_model(
            "revenue_forecaster",
            input_size=4,
            hidden_size=64,
            num_layers=2,
            forecast_horizon=7,
        )
        if model is not None:
            try:
                sequence = _build_weekly_sequence(
                    features["weekly_series"]
                )
                with torch.no_grad():
                    x = torch.tensor([sequence], dtype=torch.float32)
                    forecast_scaled = model(x)
                predictions = forecast_scaled.tolist()[0]
                forecast_egp = [
                    round(v * WEEKLY_MONEY_SCALE, 2) for v in predictions
                ]
                return _stamp_provenance({
                    "method": "neural_network",
                    "model": "RevenueForecaster",
                    "parameters": count_parameters(model),
                    "period": "week",
                    "forecast_units": "EGP",
                    "forecast": forecast_egp,
                    "total_forecast": round(sum(forecast_egp), 2),
                    "confidence": 0.80,
                }, "revenue_forecaster")
            except Exception as e:
                logger.warning("RevenueForecaster failed, falling back: %s", e)

    return _revenue_heuristic(features)


# ── Anomaly Autoencoder ──────────────────────────────────────────────


async def detect_anomalies_ann(
    db: AsyncSession,
    entity_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Detect transaction anomalies using autoencoder reconstruction error.

    Falls back to z-score heuristic if torch is unavailable.
    """
    features = await _fetch_features(db, "transactions", entity_id)
    if not features:
        return {"error": f"No transaction features found for entity {entity_id}"}

    if HAS_TORCH and "amount" in features:
        model = _load_model("anomaly_autoencoder", input_size=16, bottleneck_size=4)
        if model is not None:
            try:
                txn_ts = features.get("txn_ts")
                if isinstance(txn_ts, str):
                    txn_ts = datetime.fromisoformat(txn_ts)
                vector = build_txn_vector(
                    txn_ts,
                    features.get("amount", 0),
                    features.get("debit_amount", 0),
                    features.get("credit_amount", 0),
                    features.get("is_reconciled", 0),
                    features.get("txn_type", ""),
                )
                x = torch.tensor([vector], dtype=torch.float32)
                with torch.no_grad():
                    reconstructed, _encoded = model(x)
                reconstruction_error = torch.mean((x - reconstructed) ** 2).item()
                threshold = (
                    get_model_meta("anomaly_autoencoder").get("threshold")
                    or features.get("anomaly_threshold")
                    or 0.1
                )
                is_anomaly = reconstruction_error > threshold
                return _stamp_provenance({
                    "method": "neural_network",
                    "model": "AnomalyAutoencoder",
                    "parameters": count_parameters(model),
                    "reconstruction_error": round(reconstruction_error, 6),
                    "threshold": round(float(threshold), 8),
                    "is_anomaly": is_anomaly,
                    "confidence": round(min(0.95, 0.5 + reconstruction_error * 2), 4),
                }, "anomaly_autoencoder")
            except Exception as e:
                logger.warning("AnomalyAutoencoder failed, falling back: %s", e)

    return _anomaly_heuristic(features)


# ── Client Churn Classifier ──────────────────────────────────────────


async def predict_churn_ann(
    db: AsyncSession,
    entity_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Predict client churn probability using MLP classifier.

    DEMO/DEVELOPMENT ONLY: the current trained_models/client_churn.pt
    was trained on synthetic demo clients (scripts/seed_demo_clients.py)
    with a heuristic pseudo-label, not real churn outcomes. Results
    carry training_data/production_ready provenance fields and must
    not be surfaced as production-grade anywhere.

    Falls back to heuristic formula if torch is unavailable.
    """
    features = await _fetch_features(db, "client_churn", entity_id)
    if not features:
        return {"error": f"No churn features found for entity {entity_id}"}

    if HAS_TORCH:
        model = _load_model("client_churn", input_size=8)
        if model is not None:
            try:
                vector = _extract_churn_vector(features)
                with torch.no_grad():
                    x = torch.tensor([vector], dtype=torch.float32)
                    churn_prob = model(x).item()
                return _stamp_provenance({
                    "method": "neural_network",
                    "model": "ClientChurnClassifier",
                    "parameters": count_parameters(model),
                    "churn_probability": round(churn_prob, 4),
                    "will_churn": churn_prob > 0.5,
                    "confidence": round(max(churn_prob, 1 - churn_prob), 4),
                }, "client_churn")
            except Exception as e:
                logger.warning("ClientChurnClassifier failed, falling back: %s", e)

    return _churn_heuristic(features)


# ── Helpers ──────────────────────────────────────────────────────────


async def _fetch_features(
    db: AsyncSession, feature_group: str, entity_id: str
) -> dict[str, Any] | None:
    result = await db.execute(
        select(NeuralFeatureStore.feature_data)
        .where(
            NeuralFeatureStore.feature_group == feature_group,
            NeuralFeatureStore.feature_key == entity_id,
            NeuralFeatureStore.is_active.is_(True),
        )
        .order_by(NeuralFeatureStore.valid_from.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def _extract_feature_vector(
    features: dict[str, Any], expected_size: int = 128
) -> list[float] | None:
    values = features.get("vector")
    if isinstance(values, list) and len(values) == expected_size:
        return [float(v) for v in values]
    flat = []
    for v in features.values():
        if isinstance(v, (int, float)):
            flat.append(float(v))
    if len(flat) >= expected_size:
        return flat[:expected_size]
    while len(flat) < expected_size:
        flat.append(0.0)
    return flat


def _build_weekly_sequence(
    weekly_series: list[list[float]],
    lookback: int = REVENUE_LOOKBACK_WEEKS,
) -> list[list[float]]:
    """
    Take the last `lookback` scaled weekly rows ([rev, paid, cnt, avg])
    from a feature-store payload, zero-padding in front when fewer
    weeks are available.
    """
    rows = [list(map(float, r)) for r in weekly_series][-lookback:]
    while len(rows) < lookback:
        rows.insert(0, [0.0, 0.0, 0.0, 0.0])
    return rows


def _extract_churn_vector(features: dict[str, Any]) -> list[float]:
    keys = [
        "months_since_last_event", "total_events", "total_revenue",
        "avg_event_value", "payment_delays", "support_tickets",
        "event_frequency_trend", "revenue_trend",
    ]
    return [float(features.get(k, 0) or 0) for k in keys]


def _build_revenue_sequence(daily_revenue: list[float], lookback: int = 30) -> list[list[float]]:
    values = daily_revenue[-lookback:] if len(daily_revenue) > lookback else daily_revenue
    result = []
    for v in values:
        result.append([float(v), 0.0, 0.0, 0.0])
    while len(result) < lookback:
        result.insert(0, [0.0, 0.0, 0.0, 0.0])
    return result


def _pad_or_truncate(values: list[float], target_size: int = 16) -> list[float]:
    result = list(values[:target_size])
    while len(result) < target_size:
        result.append(0.0)
    return result


def _softmax(values: list[float]) -> list[float]:
    import math
    max_v = max(values)
    exps = [math.exp(v - max_v) for v in values]
    total = sum(exps)
    return [round(e / total, 4) for e in exps]


# ── Heuristic Fallbacks (existing logic) ─────────────────────────────


def _financial_heuristic(features: dict[str, Any]) -> dict[str, Any]:
    revenue = features.get("revenue", 0) or 0
    cost = features.get("cost", 0) or 0
    capital = features.get("capital_employed", 1) or 1
    wacc = features.get("wacc", 0.08) or 0.08
    nopat = revenue - cost
    eva = nopat - (capital * wacc)
    ebitda = nopat + (features.get("da", 0) or 0)
    return {
        "method": "heuristic",
        "eva": round(eva, 2),
        "ebitda": round(ebitda, 2),
        "risk_class": [0.7, 0.2, 0.1],
        "bsc_scores": [0.25, 0.25, 0.25, 0.25],
        "confidence": 0.50,
    }


def _revenue_heuristic(features: dict[str, Any]) -> dict[str, Any]:
    daily = features.get("daily_revenue", [])
    if not daily:
        return {"method": "heuristic", "forecast": [], "total_forecast": 0, "confidence": 0.0}
    avg = sum(daily) / len(daily)
    trend = (daily[-1] - daily[0]) / max(len(daily), 1) if len(daily) > 1 else 0
    forecast = [round(avg + trend * i, 2) for i in range(1, 8)]
    return {
        "method": "heuristic",
        "forecast": forecast,
        "total_forecast": round(sum(forecast), 2),
        "confidence": 0.45,
    }


def _anomaly_heuristic(features: dict[str, Any]) -> dict[str, Any]:
    amounts = features.get("recent_amounts", [])
    if not amounts:
        return {"method": "heuristic", "is_anomaly": False, "confidence": 0.0}
    mean = sum(amounts) / len(amounts)
    std = (sum((a - mean) ** 2 for a in amounts) / max(len(amounts), 1)) ** 0.5
    latest = amounts[-1]
    z_score = abs(latest - mean) / max(std, 0.01)
    return {
        "method": "heuristic",
        "is_anomaly": z_score > 3.0,
        "z_score": round(z_score, 4),
        "confidence": round(min(0.95, z_score / 5), 4),
    }


def _churn_heuristic(features: dict[str, Any]) -> dict[str, Any]:
    recency = features.get("months_since_last_event", 0) or 0
    frequency = features.get("total_events", 0) or 0
    churn = max(0.0, min(1.0, 0.1 * recency - 0.05 * frequency))
    return {
        "method": "heuristic",
        "churn_probability": round(churn, 4),
        "will_churn": churn > 0.5,
        "confidence": round(max(churn, 1 - churn), 4),
    }
