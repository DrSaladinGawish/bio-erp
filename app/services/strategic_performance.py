"""
BSC Persistence Service — Saves BSC scorecard results to DB and overlays
ANN-predicted perspective scores from the FinancialANN bsc_head.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def save_bsc_scorecard(
    db: AsyncSession,
    org_id: str,
    perspective_scores: list[dict],
    weighted_total_score: float,
    overall_performance_index: float,
    rating: str,
    measurement_period: str,
    ann_scores: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Save BSC scorecard result to DB."""

    perspectives_json = []
    for ps in perspective_scores:
        perspectives_json.append({
            "name": ps.get("perspective_name", ""),
            "score": ps.get("weighted_score", 0),
            "weight": ps.get("weight_pct", 25),
            "kpi_count": len(ps.get("kpis", [])),
        })

    await db.execute(text("""
        INSERT INTO stratperf_bsc_scorecards
        (id, org_id, measurement_period, perspective_scores, weighted_total_score,
         overall_performance_index, rating, ann_scores, created_at)
        VALUES (:id, :org_id, :period, :perspectives, :total, :index, :rating, :ann, :now)
    """), {
        "id": str(uuid.uuid4()),
        "org_id": str(org_id) if org_id else str(uuid.uuid4()),
        "period": measurement_period,
        "perspectives": json.dumps(perspectives_json),
        "total": weighted_total_score,
        "index": overall_performance_index,
        "rating": rating,
        "ann": json.dumps(ann_scores) if ann_scores else None,
        "now": _utcnow(),
    })
    await db.flush()

    return {
        "persisted": True,
        "ann_overlay": ann_scores is not None,
    }


async def get_bsc_history(
    db: AsyncSession, org_id: str | None = None, limit: int = 20
) -> list[dict]:
    """Fetch BSC scorecard history."""
    try:
        if org_id:
            result = await db.execute(text("""
                SELECT id, measurement_period, weighted_total_score, rating, created_at
                FROM stratperf_bsc_scorecards
                WHERE org_id = :org_id
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"org_id": str(org_id), "limit": limit})
        else:
            result = await db.execute(text("""
                SELECT id, measurement_period, weighted_total_score, rating, created_at
                FROM stratperf_bsc_scorecards
                ORDER BY created_at DESC
                LIMIT :limit
            """), {"limit": limit})

        rows = result.fetchall()
        return [
            {
                "id": row[0],
                "period": row[1],
                "total_score": row[2],
                "rating": row[3],
                "created_at": row[4].isoformat() if row[4] else None,
            }
            for row in rows
        ]
    except Exception as e:
        logger.debug("BSC history query failed (table may not exist): %s", e)
        return []


async def get_ann_bsc_scores(db: AsyncSession, org_id: str) -> dict[str, float] | None:
    """
    Try to get ANN-predicted BSC perspective scores from the FinancialANN.
    Returns dict with keys: financial, customer, internal_process, learning_growth
    """
    try:
        from app.services.neural.ann_predictors import predict_financial_ann
        result = await predict_financial_ann(db, f"bsc:{org_id}")
        if "error" not in result and result.get("method") == "neural_network":
            bsc_raw = result.get("bsc_scores", [])
            if len(bsc_raw) >= 4:
                return {
                    "financial": round(bsc_raw[0] * 100, 2),
                    "customer": round(bsc_raw[1] * 100, 2),
                    "internal_process": round(bsc_raw[2] * 100, 2),
                    "learning_growth": round(bsc_raw[3] * 100, 2),
                }
    except Exception as e:
        logger.debug("ANN BSC scores unavailable: %s", e)
    return None
