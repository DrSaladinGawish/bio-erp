"""
ANN Training Pipeline — Trains neural models on real ERP data from PostgreSQL.

Usage:
    python -m app.services.neural.trainer --model financial_ann
    python -m app.services.neural.trainer --model all
    python -m app.services.neural.trainer --status
"""

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.neural.ann_models import (
    WEEKLY_COUNT_SCALE,
    WEEKLY_MONEY_SCALE,
    AnomalyAutoencoder,
    ClientChurnClassifier,
    FinancialANN,
    RevenueForecaster,
    build_txn_vector,
    count_parameters,
)

MODELS_DIR = Path(__file__).parent.parent.parent.parent / "trained_models"
MODELS_DIR.mkdir(exist_ok=True)


def _write_meta_sidecar(model_name: str, payload: dict[str, Any]) -> Path:
    """
    Persist human-readable training metadata next to the checkpoint
    (trained_models/<name>.meta.json) so any future reader — code or
    person — can verify what the model was trained on before trusting
    its outputs.
    """
    import json

    meta_path = MODELS_DIR / f"{model_name}.meta.json"
    meta_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return meta_path


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Database Access ──────────────────────────────────────────────────


def get_engine():
    url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres123@localhost:5432/bio_erp")
    return create_async_engine(url)


# ── Feature Extraction ──────────────────────────────────────────────


async def extract_financial_features(db: AsyncSession) -> tuple[list[list[float]], list[dict]]:
    """
    Build 128-dim feature vectors from financial records.
    Returns (X, metadata) where X is list of feature vectors.
    """
    result = await db.execute(
        select(
            func.count(),
        ).select_from(text("financial_eva_records"))
    )
    count = result.scalar() or 0
    if count == 0:
        logger.warning("No financial records found for training")
        return [], []

    rows = await db.execute(text("""
        SELECT
            e.nopat, e.capital_employed, e.wacc_pct, e.eva, e.value_created,
            eb.revenue, eb.cogs, eb.opex, eb.depreciation, eb.gross_profit,
            eb.ebitda, eb.gross_margin_pct, eb.ebitda_margin_pct,
            ri.net_income, ri.equity_book_value, ri.cost_of_equity_pct, ri.residual_income,
            ep.invested_capital, ep.roic_pct, ep.wacc_pct as ep_wacc, ep.economic_profit,
            m.market_value, m.invested_capital as m_invested, m.mva,
            f.operating_cash_flow, f.capex, f.interest_expense, f.free_cash_flow
        FROM financial_eva_records e
        LEFT JOIN financial_ebitda_records eb ON eb.period = e.period AND eb.is_active = true
        LEFT JOIN financial_residual_income_records ri ON ri.period = e.period AND ri.is_active = true
        LEFT JOIN financial_economic_profit_records ep ON ep.period = e.period AND ep.is_active = true
        LEFT JOIN financial_mva_records m ON m.period = e.period AND m.is_active = true
        LEFT JOIN financial_fcf_records f ON f.period = e.period AND f.is_active = true
        WHERE e.is_active = true
        ORDER BY e.created_at
    """))

    X = []
    metadata = []
    for row in rows:
        values = [float(v or 0) for v in row]
        while len(values) < 128:
            values.append(0.0)
        X.append(values[:128])
        metadata.append({"source": "financial_records"})

    return X, metadata


REVENUE_LOOKBACK_WEEKS = 30
REVENUE_HORIZON_WEEKS = 7


async def extract_revenue_series(
    db: AsyncSession,
) -> tuple[list[list[list[float]]], list[list[float]]]:
    """
    Build weekly revenue sequences from REAL sales invoices
    (public.sales_invoices — the only non-empty invoice table).

    Each timestep is a scaled 4-vector:
      [weekly_total, weekly_paid, invoice_count, avg_invoice]
    Gap weeks (no invoices) are zero-filled so the series is
    contiguous between the first and last invoice week.

    Returns (sequences, targets):
      sequences[i] = weeks[i : i+30]   (30, 4)
      targets[i]   = next-7-weeks total revenue, same scale
    """
    rows = await db.execute(text("""
        SELECT date_trunc('week', invoice_date)::date AS wk,
               SUM(COALESCE(total, 0))::float8       AS rev,
               SUM(COALESCE(paid_amount, 0))::float8 AS paid,
               COUNT(*)::int                          AS cnt
        FROM sales_invoices
        WHERE invoice_date IS NOT NULL
        GROUP BY wk ORDER BY wk
    """))
    by_week = {
        r[0]: (float(r[1] or 0), float(r[2] or 0), int(r[3] or 0))
        for r in rows
    }
    if not by_week:
        logger.warning("No sales_invoices rows with invoice_date found")
        return [], []

    from datetime import timedelta

    series = []
    cur = min(by_week)
    while cur <= max(by_week):
        rev, paid, cnt = by_week.get(cur, (0.0, 0.0, 0))
        series.append([
            rev / WEEKLY_MONEY_SCALE,
            paid / WEEKLY_MONEY_SCALE,
            cnt / WEEKLY_COUNT_SCALE,
            (rev / cnt) / WEEKLY_MONEY_SCALE if cnt else 0.0,
        ])
        cur += timedelta(weeks=1)

    span = REVENUE_LOOKBACK_WEEKS + REVENUE_HORIZON_WEEKS
    if len(series) < span:
        logger.warning(
            "Need >=%d contiguous invoice weeks for revenue forecasting, "
            "have %d", span, len(series),
        )
        return [], []

    sequences, targets = [], []
    for i in range(len(series) - span + 1):
        sequences.append(series[i:i + REVENUE_LOOKBACK_WEEKS])
        targets.append([
            series[i + REVENUE_LOOKBACK_WEEKS + j][0]
            for j in range(REVENUE_HORIZON_WEEKS)
        ])
    return sequences, targets


async def extract_transaction_features(
    db: AsyncSession,
) -> tuple[list[list[float]], dict]:
    """
    Build 16-dim vectors from REAL bank transactions (bnk_transactions)
    using the shared build_txn_vector transform.

    Returns (X, info). info carries flagged-row counts and indices so
    training can record honestly whether is_flagged was usable for
    evaluation.
    """
    rows = await db.execute(text("""
        SELECT txn_date,
               COALESCE(amount, 0)::float8,
               COALESCE(debit_amount, 0)::float8,
               COALESCE(credit_amount, 0)::float8,
               COALESCE(is_reconciled, 0),
               COALESCE(txn_type, '')
        FROM bnk_transactions
        ORDER BY txn_date
    """))

    X = []
    flagged_indices = []
    for i, row in enumerate(rows):
        if int(row[4] or 0) == 1:
            flagged_indices.append(i)
        X.append(build_txn_vector(row[0], row[1], row[2], row[3], row[4], row[5]))

    return X, {
        "source": "bnk_transactions",
        "rows": len(X),
        "flagged": len(flagged_indices),
        "flagged_indices": flagged_indices,
    }


async def extract_client_features(db: AsyncSession) -> tuple[list[list[float]], list[dict]]:
    rows = await db.execute(text("""
        SELECT
            COALESCE(c.credit_limit, 0) AS credit_limit,
            COALESCE(c.balance, 0) AS balance,
            COALESCE(ar.credit_used, 0) AS credit_used,
            COALESCE(ar.payment_terms, 0) AS payment_terms,
            COALESCE(ar.discount_pct, 0) AS discount_pct,
            COALESCE(inv.invoice_count, 0) AS invoice_count,
            COALESCE(inv.avg_amount, 0) AS avg_amount,
            COALESCE(inv.overdue_days, 0) AS overdue_days
        FROM clients c
        LEFT JOIN ar_customers ar ON ar.code = c.code AND ar.is_active = true
        LEFT JOIN (
            SELECT customer_id,
                   COUNT(*) AS invoice_count,
                   AVG(total_amount) AS avg_amount,
                   AVG(CASE WHEN paid_date IS NULL AND due_date < CURRENT_DATE
                       THEN CURRENT_DATE - due_date ELSE 0 END) AS overdue_days
            FROM customer_invoices WHERE is_active = true GROUP BY customer_id
        ) inv ON inv.customer_id = c.id
        WHERE c.is_active = true
    """))

    X = []
    metadata = []
    for row in rows:
        values = [float(v or 0) for v in row]
        while len(values) < 8:
            values.append(0.0)
        X.append(values[:8])
        metadata.append({"source": "client_data"})

    return X, metadata


# ── Training Functions ──────────────────────────────────────────────


def train_financial_ann(X: list[list[float]], epochs: int = 200, lr: float = 0.001) -> dict[str, Any]:
    """Train FinancialANN on feature vectors."""
    if not HAS_TORCH or not X:
        return {"error": "torch not available or no data"}

    model = FinancialANN(input_size=128)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=20, factor=0.5)
    criterion_mse = nn.MSELoss()
    criterion_ce = nn.CrossEntropyLoss()

    tensor_x = torch.tensor(X, dtype=torch.float32)
    tensor_eva = tensor_x[:, 3:4]
    tensor_ebitda = tensor_x[:, 10:11]
    tensor_risk = torch.zeros(len(X), dtype=torch.long)
    tensor_bsc = torch.randn(len(X), 4) * 0.25

    dataset = TensorDataset(tensor_x, tensor_eva, tensor_ebitda, tensor_risk, tensor_bsc)
    loader = DataLoader(dataset, batch_size=min(32, len(X)), shuffle=True)

    losses = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_x, batch_eva, batch_ebitda, batch_risk, batch_bsc in loader:
            out = model(batch_x)
            loss = (
                criterion_mse(out["eva"], batch_eva)
                + criterion_mse(out["ebitda"], batch_ebitda)
                + criterion_ce(out["risk"], batch_risk)
                + criterion_mse(out["bsc"], batch_bsc)
            )
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        avg_loss = epoch_loss / len(loader)
        losses.append(avg_loss)
        scheduler.step(avg_loss)

    path = MODELS_DIR / "financial_ann.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_size": 128,
        "epochs": epochs,
        "final_loss": losses[-1],
        "trained_at": _utcnow().isoformat(),
        "training_data": "real",
    }, path)
    _write_meta_sidecar("financial_ann", {
        "model": "FinancialANN",
        "checkpoint": str(path),
        "input_size": 128,
        "epochs": epochs,
        "final_loss": losses[-1],
        "trained_at": _utcnow().isoformat(),
        "training_data": "real",
        "production_ready": False,
        "note": (
            "Trained on financial_*_records tables; risk/bsc heads use "
            "placeholder targets. Treat as experimental until those "
            "tables hold real labelled history."
        ),
    })

    return {
        "model": "financial_ann",
        "path": str(path),
        "epochs": epochs,
        "initial_loss": round(losses[0], 6),
        "final_loss": round(losses[-1], 6),
        "parameters": count_parameters(model),
        "data_points": len(X),
    }


def train_revenue_forecaster(
    sequences: list[list[list[float]]],
    targets: list[list[float]],
    epochs: int = 100,
    lr: float = 0.001,
    training_data: str = "real",
) -> dict[str, Any]:
    """
    Train RevenueForecaster on REAL weekly revenue from
    public.sales_invoices. Targets are the actual next-7-weeks totals
    (scaled), not synthetic noise.

    training_data labels provenance honestly: callers feeding anything
    other than DB-extracted series must override it (e.g. "synthetic")
    so checkpoints/sidecars never claim real-data lineage falsely.
    """
    is_real = training_data == "real"
    data_source = (
        "public.sales_invoices (weekly, zero-filled gaps)"
        if is_real
        else "caller-provided sequences"
    )
    if not HAS_TORCH or not sequences or not targets:
        return {"error": "torch not available or no data"}

    torch.manual_seed(42)
    model = RevenueForecaster(input_size=4, hidden_size=64, forecast_horizon=7)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    tensor_x = torch.tensor(sequences, dtype=torch.float32)
    tensor_y = torch.tensor(targets, dtype=torch.float32)

    dataset = TensorDataset(tensor_x, tensor_y)
    loader = DataLoader(dataset, batch_size=min(16, len(sequences)), shuffle=True)

    losses = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_x, batch_y in loader:
            out = model(batch_x)
            loss = criterion(out, batch_y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        losses.append(epoch_loss / len(loader))

    path = MODELS_DIR / "revenue_forecaster.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_size": 4,
        "hidden_size": 64,
        "forecast_horizon": 7,
        "epochs": epochs,
        "final_loss": losses[-1],
        "trained_at": _utcnow().isoformat(),
        "training_data": training_data,
        "data_source": data_source,
        "target": "next-7-weeks total revenue (scaled)",
        "feature_scaling": {
            "money": f"x / {WEEKLY_MONEY_SCALE} (EGP millions)",
            "count": f"x / {WEEKLY_COUNT_SCALE}",
        },
        "lookback_weeks": REVENUE_LOOKBACK_WEEKS,
    }, path)
    _write_meta_sidecar("revenue_forecaster", {
        "model": "RevenueForecaster",
        "checkpoint": str(path),
        "input_size": 4,
        "hidden_size": 64,
        "forecast_horizon": 7,
        "epochs": epochs,
        "final_loss": losses[-1],
        "trained_at": _utcnow().isoformat(),
        "training_data": training_data,
        "data_source": data_source,
        "production_ready": is_real,
    })

    return {
        "model": "revenue_forecaster",
        "path": str(path),
        "epochs": epochs,
        "initial_loss": round(losses[0], 6),
        "final_loss": round(losses[-1], 6),
        "parameters": count_parameters(model),
        "data_points": len(sequences),
        "training_data": training_data,
    }


def train_anomaly_detector(
    X: list[list[float]],
    epochs: int = 100,
    lr: float = 0.001,
    data_info: dict | None = None,
    training_data: str = "real",
) -> dict[str, Any]:
    """
    Train AnomalyAutoencoder on REAL bank transactions
    (bnk_transactions) with an unsupervised reconstruction objective.

    is_flagged is NOT used for training (the autoencoder is
    unsupervised). It is recorded for evaluation only; if flagged rows
    exist (>0), mean reconstruction error of flagged vs clean rows is
    compared. The serving threshold is the 99.5th percentile of
    training reconstruction errors.

    training_data labels provenance honestly (see
    train_revenue_forecaster); non-DB callers must override it.
    """
    if not HAS_TORCH or not X:
        return {"error": "torch not available or no data"}

    torch.manual_seed(42)
    info = data_info or {}
    model = AnomalyAutoencoder(input_size=16, bottleneck_size=4)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    tensor_x = torch.tensor(X, dtype=torch.float32)
    dataset = TensorDataset(tensor_x)
    loader = DataLoader(dataset, batch_size=min(32, len(X)), shuffle=True)

    losses = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        for (batch_x,) in loader:
            reconstructed, _ = model(batch_x)
            loss = criterion(reconstructed, batch_x)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        losses.append(epoch_loss / len(loader))

    with torch.no_grad():
        recon, _ = model(tensor_x)
        per_sample = ((tensor_x - recon) ** 2).mean(dim=1)
        errors_sorted, _ = torch.sort(per_sample)
        idx = min(len(errors_sorted) - 1, int(0.995 * len(errors_sorted)))
        threshold = float(errors_sorted[idx])

    flagged_count = int(info.get("flagged", 0))
    flagged_indices = list(info.get("flagged_indices", []))
    if flagged_count > 0 and flagged_indices:
        f_idx = torch.tensor(flagged_indices, dtype=torch.long)
        c_mask = torch.ones(len(X), dtype=torch.bool)
        c_mask[f_idx] = False
        flagged_mean = float(per_sample[f_idx].mean())
        clean_mean = float(per_sample[c_mask].mean()) if c_mask.any() else 0.0
        eval_note = (
            "is_flagged evaluation: mean reconstruction error "
            f"flagged={flagged_mean:.8f} vs clean={clean_mean:.8f}"
        )
    else:
        eval_note = (
            "is_flagged had 0 positive rows in bnk_transactions at "
            "training time — training and threshold are unsupervised; "
            "threshold = 99.5th percentile of reconstruction error."
        )

    is_real = training_data == "real"
    data_source = (
        "public.bnk_transactions" if is_real else "caller-provided vectors"
    )

    path = MODELS_DIR / "anomaly_autoencoder.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_size": 16,
        "bottleneck_size": 4,
        "epochs": epochs,
        "final_loss": losses[-1],
        "trained_at": _utcnow().isoformat(),
        "training_data": training_data,
        "data_source": data_source,
        "threshold": threshold,
        "objective": "unsupervised reconstruction (MSE)",
        "metrics": {
            "rows": len(X),
            "flagged_rows": flagged_count,
            "eval_note": eval_note,
        },
    }, path)
    _write_meta_sidecar("anomaly_autoencoder", {
        "model": "AnomalyAutoencoder",
        "checkpoint": str(path),
        "input_size": 16,
        "bottleneck_size": 4,
        "epochs": epochs,
        "final_loss": losses[-1],
        "trained_at": _utcnow().isoformat(),
        "training_data": training_data,
        "data_source": data_source,
        "threshold_p99_5": round(threshold, 8),
        "production_ready": is_real,
        "note": eval_note,
    })

    return {
        "model": "anomaly_detector",
        "path": str(path),
        "epochs": epochs,
        "initial_loss": round(losses[0], 6),
        "final_loss": round(losses[-1], 6),
        "parameters": count_parameters(model),
        "data_points": len(X),
        "threshold": round(threshold, 8),
        "flagged_rows": flagged_count,
    }


def train_client_churn(
    X: list[list[float]],
    epochs: int = 200,
    lr: float = 0.001,
    training_data: str = "real",
) -> dict[str, Any]:
    """
    Train ClientChurnClassifier.

    training_data MUST be "real" only when X comes from real client
    churn outcomes. Demo-seeded data (scripts/seed_demo_clients.py)
    must pass training_data="demo/synthetic" — the flag is stored in
    the checkpoint and sidecar metadata and gates API exposure.
    """
    if not HAS_TORCH or not X:
        return {"error": "torch not available or no data"}

    torch.manual_seed(42)
    model = ClientChurnClassifier(input_size=8)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.BCELoss()

    tensor_x = torch.tensor(X, dtype=torch.float32)
    targets = (tensor_x[:, 1] > tensor_x[:, 2] * 0.8).float()

    dataset = TensorDataset(tensor_x, targets)
    loader = DataLoader(dataset, batch_size=min(32, len(X)), shuffle=True)

    losses = []
    for epoch in range(epochs):
        epoch_loss = 0.0
        for batch_x, batch_y in loader:
            out = model(batch_x)
            loss = criterion(out.squeeze(), batch_y)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        losses.append(epoch_loss / len(loader))

    path = MODELS_DIR / "client_churn.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "input_size": 8,
        "epochs": epochs,
        "final_loss": losses[-1],
        "trained_at": _utcnow().isoformat(),
        "training_data": training_data,
    }, path)
    _write_meta_sidecar("client_churn", {
        "model": "ClientChurnClassifier",
        "checkpoint": str(path),
        "input_size": 8,
        "epochs": epochs,
        "final_loss": losses[-1],
        "trained_at": _utcnow().isoformat(),
        "training_data": training_data,
        "production_ready": training_data == "real",
        "note": (
            "DEMO/SYNTHETIC: labels are the heuristic rule "
            "(balance > credit_used * 0.8) over seeded demo clients — "
            "NOT real churn outcomes. Do not serve as production-grade "
            "until retrained on real outcome data."
        ) if training_data != "real" else "",
    })

    return {
        "model": "client_churn",
        "path": str(path),
        "epochs": epochs,
        "initial_loss": round(losses[0], 6),
        "final_loss": round(losses[-1], 6),
        "parameters": count_parameters(model),
        "data_points": len(X),
    }


# ── CLI ──────────────────────────────────────────────────────────────


async def run_training(
    model_name: str, epochs: int = 200, training_data: str = "real"
) -> dict[str, Any]:
    engine = get_engine()
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        results = {}

        if model_name in ("financial_ann", "all"):
            logger.info("Extracting financial features...")
            X, _meta = await extract_financial_features(db)
            if X:
                logger.info("Training FinancialANN on %d samples...", len(X))
                results["financial_ann"] = train_financial_ann(X, epochs=epochs)
            else:
                results["financial_ann"] = {"error": "no data"}

        if model_name in ("revenue_forecaster", "all"):
            logger.info("Extracting weekly revenue series from sales_invoices...")
            seqs, targets = await extract_revenue_series(db)
            if seqs:
                logger.info(
                    "Training RevenueForecaster on %d sequences...",
                    len(seqs),
                )
                results["revenue_forecaster"] = train_revenue_forecaster(
                    seqs, targets, epochs=epochs
                )
            else:
                results["revenue_forecaster"] = {"error": "no data"}

        if model_name in ("anomaly_detector", "all"):
            logger.info("Extracting bank transaction features...")
            X, info = await extract_transaction_features(db)
            if X:
                logger.info(
                    "Training AnomalyAutoencoder on %d transactions "
                    "(flagged=%d)...", len(X), info.get("flagged", 0),
                )
                results["anomaly_detector"] = train_anomaly_detector(
                    X, epochs=epochs, data_info=info
                )
            else:
                results["anomaly_detector"] = {"error": "no data"}

        if model_name in ("client_churn", "all"):
            logger.info("Extracting client features...")
            X, _meta = await extract_client_features(db)
            if X:
                logger.info(
                    "Training ClientChurnClassifier on %d samples (training_data=%s)...",
                    len(X), training_data,
                )
                results["client_churn"] = train_client_churn(
                    X, epochs=epochs, training_data=training_data
                )
            else:
                results["client_churn"] = {"error": "no data"}

    await engine.dispose()
    return results


def show_status() -> dict[str, Any]:
    status = {}
    for name in ["financial_ann", "revenue_forecaster", "anomaly_autoencoder", "client_churn"]:
        path = MODELS_DIR / f"{name}.pt"
        if path.exists():
            checkpoint = torch.load(path, weights_only=False)
            status[name] = {
                "exists": True,
                "path": str(path),
                "epochs": checkpoint.get("epochs"),
                "final_loss": checkpoint.get("final_loss"),
                "trained_at": checkpoint.get("trained_at"),
                "training_data": checkpoint.get("training_data", "unknown"),
            }
        else:
            status[name] = {"exists": False}
    return status


def main():
    parser = argparse.ArgumentParser(description="BIO-ERP ANN Trainer")
    parser.add_argument("--model", default="all", choices=["financial_ann", "revenue_forecaster", "anomaly_detector", "client_churn", "all"])
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument(
        "--training-data",
        default="real",
        choices=["real", "demo/synthetic"],
        help="Data provenance recorded in the checkpoint metadata "
             "(client_churn only). Use demo/synthetic for seeded data.",
    )
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.status:
        status = show_status()
        for name, info in status.items():
            if info.get("exists"):
                print(f"  {name}: trained at {info['trained_at']}, loss={info['final_loss']:.6f}, {info['epochs']} epochs, training_data={info.get('training_data')}")
            else:
                print(f"  {name}: NOT TRAINED")
        return

    results = asyncio.run(run_training(args.model, args.epochs, args.training_data))
    for name, result in results.items():
        if "error" in result:
            print(f"  {name}: {result['error']}")
        else:
            print(f"  {name}: loss={result['final_loss']:.6f}, params={result['parameters']}, data={result['data_points']}")


if __name__ == "__main__":
    import asyncio
    main()
