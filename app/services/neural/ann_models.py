"""
BIO-ERP Neural Network Models — Real ANN implementations.

These models plug into the existing neural subsystem scaffold:
- NeuralFeatureStore → input features
- NeuralPrediction → stored results
- NeuralTrainingHistory → training metadata

All models use graceful degradation: if torch is unavailable,
predictors fall back to the existing heuristic methods.
"""

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.warning("torch not available — ANN models disabled, using heuristic fallback")


# ── Shared Feature Builders ──────────────────────────────────────────
#
# Single source of truth for the feature transforms used by BOTH
# trainer.py (training) and ann_predictors.py (serving). Changing a
# transform here invalidates existing checkpoints for that model —
# retrain before serving.

WEEKLY_MONEY_SCALE = 1e6  # EGP → millions
WEEKLY_COUNT_SCALE = 10.0  # invoice count → tens

REVENUE_FEATURE_NAMES = [
    "weekly_revenue_m",
    "weekly_collected_m",
    "invoice_count_tens",
    "avg_invoice_m",
]

TXN_TYPE_BUCKETS = (
    "CHARGES",          # bank fees / charges
    "CARD",             # ATM TRA, POS
    "TRANSFER",         # W.Trans, Internal
    "OTHER",            # RCT, CHQ, empty, unknown
)


def _bucket_index(txn_type: str) -> int:
    t = (txn_type or "").strip().upper()
    if t == "CHARGES":
        return 0
    if t in ("ATM TRA", "POS"):
        return 1
    if t in ("W.TRANS", "INTERNAL"):
        return 2
    return 3


def build_txn_vector(
    txn_ts,
    amount: float,
    debit: float,
    credit: float,
    is_reconciled: int | bool,
    txn_type: str,
) -> list[float]:
    """
    Deterministic 16-dim bounded feature vector for one bank
    transaction. Same function is used at training and serving time.

    Layout:
      0  log1p(|amount|)/14
      1  log1p(debit)/14
      2  log1p(credit)/14
      3  debit share of (debit+credit)
      4  is_reconciled
      5  hour sin        6  hour cos
      7  weekday sin     8  weekday cos
      9  is_weekend
      10 month sin      11 month cos
      12-15 txn-type one-hot bucket (CHARGES/CARD/TRANSFER/OTHER)
    """
    ts = txn_ts or __import__("datetime").datetime(2000, 1, 1)
    amt = max(float(amount or 0), 0.0)
    deb = max(float(debit or 0), 0.0)
    cre = max(float(credit or 0), 0.0)
    total_dc = deb + cre

    vec = [
        math.log1p(amt) / 14.0,
        math.log1p(deb) / 14.0,
        math.log1p(cre) / 14.0,
        deb / total_dc if total_dc > 0 else 0.5,
        float(bool(is_reconciled)),
    ]

    hour = getattr(ts, "hour", 12) + getattr(ts, "minute", 0) / 60.0
    dow = getattr(ts, "weekday", None)
    dow_idx = dow() if callable(dow) else 0
    weekend = dow_idx >= 5
    month = getattr(ts, "month", 1)

    vec += [
        math.sin(2 * math.pi * hour / 24),
        math.cos(2 * math.pi * hour / 24),
        math.sin(2 * math.pi * dow_idx / 7),
        math.cos(2 * math.pi * dow_idx / 7),
        1.0 if weekend else 0.0,
        math.sin(2 * math.pi * (month - 1) / 12),
        math.cos(2 * math.pi * (month - 1) / 12),
    ]
    bucket = [0.0] * len(TXN_TYPE_BUCKETS)
    bucket[_bucket_index(txn_type)] = 1.0
    return vec + bucket


TXN_VECTOR_SIZE = 16


class FinancialANN(nn.Module):
    """
    Multi-head feedforward network for financial KPI prediction.

    Input:  128 ERP features (financial, operational, market, HR)
    Encoder: 128 → 256 → 128 → 64 (BatchNorm + ReLU + Dropout)
    Heads:
      - eva_head:    64 → 1  (EVA regression)
      - ebitda_head: 64 → 1  (EBITDA regression)
      - risk_head:   64 → 3  (risk classification: low/medium/high)
      - bsc_head:    64 → 4  (BSC perspective scores)
    """

    def __init__(self, input_size: int = 128):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_size, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
        )
        self.eva_head = nn.Linear(64, 1)
        self.ebitda_head = nn.Linear(64, 1)
        self.risk_head = nn.Linear(64, 3)
        self.bsc_head = nn.Linear(64, 4)

    def forward(self, x: "torch.Tensor") -> dict[str, "torch.Tensor"]:
        features = self.encoder(x)
        return {
            "eva": self.eva_head(features),
            "ebitda": self.ebitda_head(features),
            "risk": self.risk_head(features),
            "bsc": self.bsc_head(features),
        }


class RevenueForecaster(nn.Module):
    """
    LSTM-based time-series revenue forecaster.

    Input:  (batch, lookback_days, features_per_day)
    Output: (batch, forecast_horizon) — daily revenue predictions
    """

    def __init__(
        self,
        input_size: int = 4,
        hidden_size: int = 64,
        num_layers: int = 2,
        forecast_horizon: int = 7,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, forecast_horizon),
        )

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]
        return self.fc(last_hidden)


class AnomalyAutoencoder(nn.Module):
    """
    Autoencoder for transaction anomaly detection.

    Architecture: input → encoder → bottleneck → decoder → reconstruction
    Anomaly = high reconstruction error
    """

    def __init__(self, input_size: int = 16, bottleneck_size: int = 4):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_size, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, bottleneck_size),
        )
        self.decoder = nn.Sequential(
            nn.Linear(bottleneck_size, 16),
            nn.ReLU(),
            nn.Linear(16, 32),
            nn.ReLU(),
            nn.Linear(32, input_size),
        )

    def forward(self, x: "torch.Tensor") -> tuple["torch.Tensor", "torch.Tensor"]:
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded, encoded


class ClientChurnClassifier(nn.Module):
    """
    MLP classifier for client churn prediction.

    Input:  Client RFM features + behavioral signals
    Output: churn probability (0-1)
    """

    def __init__(self, input_size: int = 8):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 32),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: "torch.Tensor") -> "torch.Tensor":
        return self.network(x)


# ── Utility ──────────────────────────────────────────────────────────


def get_model(model_name: str, **kwargs: Any) -> "nn.Module | None":
    """Factory: return instantiated model by name, or None if torch unavailable."""
    if not HAS_TORCH:
        return None
    models = {
        "financial_ann": FinancialANN,
        "revenue_forecaster": RevenueForecaster,
        "anomaly_autoencoder": AnomalyAutoencoder,
        "client_churn": ClientChurnClassifier,
    }
    cls = models.get(model_name)
    if cls is None:
        raise ValueError(f"Unknown model: {model_name}. Available: {list(models.keys())}")
    return cls(**kwargs)


def count_parameters(model: "nn.Module") -> int:
    """Return total trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
