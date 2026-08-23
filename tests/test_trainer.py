"""ANN Trainer Tests — verify the training pipeline end-to-end.

Checkpoints are written to an isolated temp dir so tests never clobber
the production trained_models/ artifacts (real-data checkpoints carry
provenance that must survive test runs).
"""

import os
import random
import sys

import pytest

sys.path.insert(0, r"ERP System/BIO_ERP")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp")
os.environ.setdefault("DATABASE_URL_READONLY", "postgresql+asyncpg://bio_erp_reader:DXqF5mW7Hcz4AIg9nSCMFroeyqZegS74thwxuxQVwPQ@localhost:5432/bio_erp")

from app.services.neural import trainer as trainer_mod  # noqa: E402
from app.services.neural.ann_models import HAS_TORCH  # noqa: E402
from app.services.neural.trainer import (  # noqa: E402
    show_status,
    train_anomaly_detector,
    train_financial_ann,
    train_revenue_forecaster,
)

pytestmark = pytest.mark.skipif(not HAS_TORCH, reason="torch unavailable")


@pytest.fixture(scope="module", autouse=True)
def isolated_model_dir(tmp_path_factory):
    """Redirect checkpoint + meta-sidecar writes away from trained_models/."""
    original = trainer_mod.MODELS_DIR
    sandbox = tmp_path_factory.mktemp("trained_models")
    trainer_mod.MODELS_DIR = sandbox
    yield sandbox
    trainer_mod.MODELS_DIR = original


# ── Group 1: FinancialANN Training ───────────────────────────────────


def test_train_financial_ann(isolated_model_dir):
    import torch

    random.seed(42)
    x_fin = [[random.gauss(0, 1) for _ in range(128)] for _ in range(50)]
    result = train_financial_ann(x_fin, epochs=30, lr=0.001)

    assert "error" not in result
    assert result["final_loss"] < result["initial_loss"]
    assert os.path.exists(result["path"])
    assert result["data_points"] == 50

    checkpoint = torch.load(result["path"], weights_only=False)
    assert "model_state_dict" in checkpoint
    assert "trained_at" in checkpoint
    assert str(isolated_model_dir) in result["path"]


# ── Group 2: RevenueForecaster Training ──────────────────────────────


def test_train_revenue_forecaster(isolated_model_dir):
    import torch

    random.seed(42)
    seqs = [
        [[random.gauss(100, 10) for _ in range(4)] for _ in range(30)]
        for _ in range(20)
    ]
    targets = [
        [random.gauss(100, 10) for _ in range(7)] for _ in range(20)
    ]

    result = train_revenue_forecaster(
        seqs, targets, epochs=20, lr=0.001, training_data="synthetic"
    )

    assert "error" not in result
    assert result["final_loss"] < result["initial_loss"]
    assert os.path.exists(result["path"])
    assert result["training_data"] == "synthetic"
    checkpoint = torch.load(result["path"], weights_only=False)
    assert checkpoint["training_data"] == "synthetic"
    assert str(isolated_model_dir) in result["path"]


# ── Group 3: AnomalyAutoencoder Training ─────────────────────────────


def test_train_anomaly_detector(isolated_model_dir):
    import torch

    random.seed(42)
    x_ano = [[random.gauss(0, 1) for _ in range(16)] for _ in range(50)]
    result = train_anomaly_detector(
        x_ano, epochs=20, lr=0.001, data_info={"flagged": 0},
        training_data="synthetic",
    )

    assert "error" not in result
    assert result["final_loss"] < result["initial_loss"]
    assert os.path.exists(result["path"])

    checkpoint = torch.load(result["path"], weights_only=False)
    assert "threshold" in checkpoint
    assert checkpoint["training_data"] == "synthetic"
    assert checkpoint["metrics"]["eval_note"]
    assert str(isolated_model_dir) in result["path"]


# ── Group 4: Status ──────────────────────────────────────────────────


def test_show_status_reports_trained_models():
    status = show_status()

    assert "financial_ann" in status
    assert status["financial_ann"]["exists"] is True
    assert status["revenue_forecaster"]["exists"] is True
    assert status["anomaly_autoencoder"]["exists"] is True
    assert "training_data" in status["financial_ann"]
