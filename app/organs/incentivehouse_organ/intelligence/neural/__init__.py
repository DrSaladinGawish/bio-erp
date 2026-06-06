"""
intelligence/neural/__init__.py
Neural predictors for IHE-ERP.
5 predictors: cashflow, anomaly, client score, revenue forecast, vendor rank.
"""
from __future__ import annotations
import logging
import math
import statistics
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("incentivehouse_organ.intelligence.neural")


def _fetch_amounts(db: Session, table: str, amount_col: str, date_col: str) -> list:
    """Fetch (date, amount) tuples for time-series analysis."""
    try:
        rows = db.execute(text(
            f"SELECT {date_col}, {amount_col} FROM {table} WHERE {amount_col} IS NOT NULL ORDER BY {date_col} DESC LIMIT 200"
        )).fetchall()
        return [(r[0], float(r[1] or 0)) for r in rows]
    except Exception as exc:
        logger.debug("_fetch_amounts(%s) failed: %s", table, exc)
        return []


def _linear_forecast(values: list, horizon: int = 7) -> list:
    """Simple linear regression forecast.  Returns `horizon` future values."""
    if len(values) < 2:
        return [values[-1] if values else 0.0] * horizon
    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    num = sum((xs[i] - mean_x) * (values[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    slope = num / den if den else 0
    intercept = mean_y - slope * mean_x
    return [max(0.0, slope * (n + i) + intercept) for i in range(1, horizon + 1)]


def predict_cashflow(db: Session, horizon_days: int = 7) -> dict:
    """Forecast cashflow for the next N days from bank_transaction history."""
    series = _fetch_amounts(db, "bank_transaction", "amount", "transaction_date")
    if not series:
        series = _fetch_amounts(db, "bnk_transaction", "amount", "transaction_date")
    amounts = [a for _, a in reversed(series)]
    forecast = _linear_forecast(amounts, horizon_days)
    return {
        "predictor": "cashflow",
        "horizon_days": horizon_days,
        "history_points": len(amounts),
        "forecast": [round(x, 2) for x in forecast],
        "total_forecast": round(sum(forecast), 2),
        "trend": "up" if (forecast[-1] > amounts[-1] if amounts else 0) else "down",
        "confidence": min(1.0, len(amounts) / 30.0),
        "generated_at": datetime.now().isoformat(),
    }


def predict_revenue(db: Session, horizon_days: int = 7) -> dict:
    """Forecast revenue from sales_invoice history."""
    series = _fetch_amounts(db, "sales_invoice", "total_amount", "invoice_date")
    amounts = [a for _, a in reversed(series)]
    forecast = _linear_forecast(amounts, horizon_days)
    return {
        "predictor": "revenue",
        "horizon_days": horizon_days,
        "history_points": len(amounts),
        "forecast": [round(x, 2) for x in forecast],
        "total_forecast": round(sum(forecast), 2),
        "confidence": min(1.0, len(amounts) / 30.0),
        "generated_at": datetime.now().isoformat(),
    }


def detect_anomalies(db: Session) -> dict:
    """Detect outlier bank transactions using z-score > 3."""
    series = _fetch_amounts(db, "bank_transaction", "amount", "transaction_date")
    if not series:
        return {"predictor": "anomaly", "anomalies": [], "scanned": 0}
    amounts = [a for _, a in series]
    if len(amounts) < 5:
        return {"predictor": "anomaly", "anomalies": [], "scanned": len(amounts),
                "note": "Need >=5 transactions for meaningful detection"}
    mean = statistics.mean(amounts)
    stdev = statistics.stdev(amounts) if len(amounts) > 1 else 0
    if stdev == 0:
        return {"predictor": "anomaly", "anomalies": [], "scanned": len(amounts)}
    anomalies = []
    for date, amt in series:
        z = abs((amt - mean) / stdev)
        if z > 3:
            anomalies.append({"date": str(date), "amount": amt, "z_score": round(z, 2)})
    return {
        "predictor": "anomaly",
        "scanned": len(amounts),
        "mean": round(mean, 2),
        "stdev": round(stdev, 2),
        "anomalies": anomalies[:20],
        "generated_at": datetime.now().isoformat(),
    }


def score_clients(db: Session) -> dict:
    """Score clients by total sales (simple ranking)."""
    try:
        rows = db.execute(text("""
            SELECT client_id, COALESCE(SUM(total_amount), 0) as total, COUNT(*) as cnt
            FROM sales_invoice
            GROUP BY client_id
            ORDER BY total DESC
            LIMIT 20
        """)).fetchall()
        clients = [{"client_id": r[0], "total_sales": float(r[1]), "invoice_count": r[2],
                    "score": round(min(100, float(r[1]) / 1000.0), 1)} for r in rows]
    except Exception as exc:
        logger.debug("score_clients failed: %s", exc)
        clients = []
    return {
        "predictor": "client_score",
        "scored": len(clients),
        "clients": clients,
        "generated_at": datetime.now().isoformat(),
    }


def rank_vendors(db: Session) -> dict:
    """Rank vendors by total spend."""
    try:
        rows = db.execute(text("""
            SELECT vendor_id, COALESCE(SUM(total_amount), 0) as total, COUNT(*) as cnt
            FROM purchase_voucher
            GROUP BY vendor_id
            ORDER BY total DESC
            LIMIT 20
        """)).fetchall()
        vendors = [{"vendor_id": r[0], "total_spend": float(r[1]), "voucher_count": r[2],
                    "rank": i + 1} for i, r in enumerate(rows)]
    except Exception as exc:
        logger.debug("rank_vendors failed: %s", exc)
        vendors = []
    return {
        "predictor": "vendor_rank",
        "scored": len(vendors),
        "vendors": vendors,
        "generated_at": datetime.now().isoformat(),
    }


def run_all_predictors(db: Session) -> dict:
    """Run all 5 predictors and return a combined report."""
    return {
        "version": "2.3.0",
        "generated_at": datetime.now().isoformat(),
        "cashflow": predict_cashflow(db),
        "revenue": predict_revenue(db),
        "anomaly": detect_anomalies(db),
        "client_score": score_clients(db),
        "vendor_rank": rank_vendors(db),
    }
