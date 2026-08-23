from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.neural.prediction import (
    NeuralPrediction,
    NeuralFeatureStore,
    NeuralTrainingHistory,
    NeuralMemory,
)
from app.services.neural.ann_predictors import (
    predict_financial_ann,
    predict_revenue_ann,
    detect_anomalies_ann,
    predict_churn_ann,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CashFlowPredictor:
    @staticmethod
    async def predict(
        db: AsyncSession, entity_id: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        features = await db.execute(
            select(NeuralFeatureStore.feature_data)
            .where(
                NeuralFeatureStore.feature_group == "cash_flow",
                NeuralFeatureStore.feature_key == entity_id,
                NeuralFeatureStore.is_active.is_(True),
            )
            .order_by(NeuralFeatureStore.valid_from.desc())
            .limit(1)
        )
        feature_row = features.scalar_one_or_none()
        if not feature_row:
            return {"error": f"No features found for entity {entity_id}"}

        avg_inflow = feature_row.get("avg_monthly_inflow", 0) or 0
        avg_outflow = feature_row.get("avg_monthly_outflow", 0) or 0
        current_balance = feature_row.get("current_balance", 0) or 0
        trend_factor = 1.0 + (feature_row.get("growth_rate", 0) or 0)

        projected_balance = (
            current_balance + (avg_inflow - avg_outflow) * trend_factor * 3
        )
        confidence = min(
            0.95, max(0.3, 1.0 - (abs(avg_inflow - avg_outflow) / (avg_inflow + 0.01)))
        )

        return {
            "predicted_value": round(projected_balance, 2),
            "confidence": round(confidence, 4),
            "current_balance": current_balance,
            "avg_inflow": avg_inflow,
            "avg_outflow": avg_outflow,
            "projected_3mo": round(projected_balance, 2),
        }


class ClientChurnPredictor:
    @staticmethod
    async def predict(
        db: AsyncSession, entity_id: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        features = await db.execute(
            select(NeuralFeatureStore.feature_data)
            .where(
                NeuralFeatureStore.feature_group == "churn",
                NeuralFeatureStore.feature_key == entity_id,
                NeuralFeatureStore.is_active.is_(True),
            )
            .order_by(NeuralFeatureStore.valid_from.desc())
            .limit(1)
        )
        feature_row = features.scalar_one_or_none()
        if not feature_row:
            return {"error": f"No features found for client {entity_id}"}

        recency = feature_row.get("months_since_last_event", 12) or 12
        frequency = feature_row.get("events_per_year", 1) or 1
        avg_revenue = feature_row.get("avg_revenue_per_event", 0) or 0

        churn_prob = min(0.95, max(0.05, 0.1 * recency - 0.05 * frequency))
        confidence = min(0.9, max(0.3, 1.0 - (recency / 24)))

        return {
            "predicted_value": round(churn_prob, 4),
            "confidence": round(confidence, 4),
            "churn_probability_pct": round(churn_prob * 100, 2),
            "risk_level": "high"
            if churn_prob > 0.6
            else "medium"
            if churn_prob > 0.3
            else "low",
            "months_since_last_event": recency,
            "events_per_year": frequency,
            "avg_revenue_per_event": avg_revenue,
        }


class PnrOverrunPredictor:
    @staticmethod
    async def predict(
        db: AsyncSession, entity_id: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        features = await db.execute(
            select(NeuralFeatureStore.feature_data)
            .where(
                NeuralFeatureStore.feature_group == "pnr",
                NeuralFeatureStore.feature_key == entity_id,
                NeuralFeatureStore.is_active.is_(True),
            )
            .order_by(NeuralFeatureStore.valid_from.desc())
            .limit(1)
        )
        feature_row = features.scalar_one_or_none()
        if not feature_row:
            return {"error": f"No features found for PNR {entity_id}"}

        budget = feature_row.get("budget", 1) or 1
        spent = feature_row.get("spent_to_date", 0) or 0
        completion_pct = feature_row.get("completion_pct", 50) or 50
        historical_overrun = feature_row.get("historical_overrun_pct", 0) or 0

        projected_total = spent / (completion_pct / 100 + 0.01)
        overrun_pct = ((projected_total - budget) / budget) * 100
        confidence = min(0.85, max(0.2, 1.0 - (completion_pct / 200)))

        return {
            "predicted_value": round(overrun_pct, 2),
            "confidence": round(confidence, 4),
            "overrun_pct": round(overrun_pct, 2),
            "projected_total": round(projected_total, 2),
            "budget": budget,
            "spent_to_date": spent,
            "completion_pct": completion_pct,
            "historical_overrun_pct": historical_overrun,
        }


class TransactionAnomalyDetector:
    @staticmethod
    async def predict(
        db: AsyncSession, entity_id: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        features = await db.execute(
            select(NeuralFeatureStore.feature_data)
            .where(
                NeuralFeatureStore.feature_group == "anomaly",
                NeuralFeatureStore.feature_key == entity_id,
                NeuralFeatureStore.is_active.is_(True),
            )
            .order_by(NeuralFeatureStore.valid_from.desc())
            .limit(1)
        )
        feature_row = features.scalar_one_or_none()
        if not feature_row:
            return {"error": f"No features found for transaction {entity_id}"}

        amount = feature_row.get("amount", 0) or 0
        avg_amount = feature_row.get("avg_amount", 1) or 1
        std_amount = feature_row.get("std_amount", avg_amount * 0.3) or 1
        z_score = (amount - avg_amount) / (std_amount + 0.01)
        is_weekend = feature_row.get("is_weekend", False)
        is_unusual_hour = feature_row.get("is_unusual_hour", False)
        new_vendor = feature_row.get("is_new_vendor", False)

        anomaly_score = min(1.0, max(0.0, abs(z_score) / 5))
        if is_weekend:
            anomaly_score += 0.1
        if is_unusual_hour:
            anomaly_score += 0.15
        if new_vendor:
            anomaly_score += 0.2
        anomaly_score = min(1.0, anomaly_score)

        confidence = min(0.9, max(0.3, 1.0 - (1.0 / (1 + abs(z_score)))))

        return {
            "predicted_value": round(anomaly_score, 4),
            "confidence": round(confidence, 4),
            "anomaly_score": round(anomaly_score, 4),
            "is_anomaly": anomaly_score > 0.6,
            "z_score": round(z_score, 2),
            "amount": amount,
            "avg_amount": avg_amount,
            "risk_factors": {
                "weekend": is_weekend,
                "unusual_hour": is_unusual_hour,
                "new_vendor": new_vendor,
            },
        }


# ── ANN-backed predictors (wrap async functions into class interface) ──


class FinancialANNPredictor:
    @staticmethod
    async def predict(db: AsyncSession, entity_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await predict_financial_ann(db, entity_id, context)
        if "eva" in result:
            result["predicted_value"] = result["eva"]
        return result


class RevenueForecasterPredictor:
    @staticmethod
    async def predict(db: AsyncSession, entity_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await predict_revenue_ann(db, entity_id, context)
        if "total_forecast" in result:
            result["predicted_value"] = result["total_forecast"]
        return result


class AnomalyDetectorPredictor:
    @staticmethod
    async def predict(db: AsyncSession, entity_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await detect_anomalies_ann(db, entity_id, context)
        if "reconstruction_error" in result:
            result["predicted_value"] = result["reconstruction_error"]
        return result


class ChurnClassifierPredictor:
    @staticmethod
    async def predict(db: AsyncSession, entity_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        result = await predict_churn_ann(db, entity_id, context)
        if "churn_probability" in result:
            result["predicted_value"] = result["churn_probability"]
        return result


class PredictorService:
    PREDICTORS: dict[str, Any] = {
        "cash_flow": CashFlowPredictor,
        "client_churn": ClientChurnPredictor,
        "pnr_overrun": PnrOverrunPredictor,
        "transaction_anomaly": TransactionAnomalyDetector,
        "financial_ann": FinancialANNPredictor,
        "revenue_forecast": RevenueForecasterPredictor,
        "anomaly_detector": AnomalyDetectorPredictor,
        "churn_classifier": ChurnClassifierPredictor,
    }

    @staticmethod
    def _prediction_to_dict(p: NeuralPrediction) -> dict[str, Any]:
        return {
            "id": p.id,
            "prediction_type": p.prediction_type,
            "prediction_key": p.prediction_key,
            "predicted_value": p.predicted_value,
            "confidence": p.confidence,
            "actual_value": p.actual_value,
            "features_snapshot": p.features_snapshot,
            "model_version": p.model_version,
            "prediction_date": p.prediction_date.isoformat()
            if p.prediction_date
            else None,
            "metadata_json": p.metadata_json,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }

    @staticmethod
    async def predict(
        db: AsyncSession,
        prediction_type: str,
        entity_id: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        predictor_cls = PredictorService.PREDICTORS.get(prediction_type)
        if not predictor_cls:
            return {"error": f"Unknown prediction type: {prediction_type}"}

        result = await predictor_cls.predict(db, entity_id, context)
        if "error" in result:
            return result

        if result.get("predicted_value") is not None:
            method = result.get("method", "heuristic")
            model_name = result.get("model", prediction_type)
            version = "2.0-ann" if method == "neural_network" else "1.0-heuristic"
            prediction = NeuralPrediction(
                prediction_type=prediction_type,
                prediction_key=entity_id,
                predicted_value=result["predicted_value"],
                confidence=result.get("confidence", 0.0),
                features_snapshot=result,
                model_version=f"{model_name}/{version}",
                prediction_date=_utcnow(),
            )
            db.add(prediction)
            await db.commit()
            await db.refresh(prediction)
            result["prediction_id"] = prediction.id

        return result

    @staticmethod
    async def submit_feedback(
        db: AsyncSession, prediction_id: int, actual_value: float
    ) -> dict[str, Any]:
        pred = await db.execute(
            select(NeuralPrediction).where(NeuralPrediction.id == prediction_id)
        )
        prediction = pred.scalar_one_or_none()
        if not prediction:
            return {"error": f"Prediction {prediction_id} not found"}

        prediction.actual_value = actual_value
        await db.commit()
        await db.refresh(prediction)
        return {
            "status": "ok",
            "prediction_id": prediction.id,
            "actual_value": actual_value,
        }

    @staticmethod
    async def list_predictions(
        db: AsyncSession,
        prediction_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> dict[str, Any]:
        query = select(NeuralPrediction).order_by(NeuralPrediction.created_at.desc())
        count_query = select(func.count(NeuralPrediction.id))
        if prediction_type:
            query = query.where(NeuralPrediction.prediction_type == prediction_type)
            count_query = count_query.where(
                NeuralPrediction.prediction_type == prediction_type
            )

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        total_pages = max(1, (total + page_size - 1) // page_size)

        result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
        items = [
            PredictorService._prediction_to_dict(p) for p in result.scalars().all()
        ]

        return {
            "data": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    @staticmethod
    async def get_dashboard(db: AsyncSession) -> dict[str, Any]:
        total = await db.execute(select(func.count(NeuralPrediction.id)))
        total_predictions = total.scalar() or 0

        by_type_result = await db.execute(
            select(
                NeuralPrediction.prediction_type, func.count(NeuralPrediction.id)
            ).group_by(NeuralPrediction.prediction_type)
        )
        by_type = dict(by_type_result.all())

        avg_conf = await db.execute(
            select(func.avg(NeuralPrediction.confidence)).where(
                NeuralPrediction.is_active.is_(True)
            )
        )
        avg_confidence = round(avg_conf.scalar() or 0, 4)

        recent = await db.execute(
            select(NeuralPrediction)
            .order_by(NeuralPrediction.created_at.desc())
            .limit(5)
        )
        recent_predictions = [
            PredictorService._prediction_to_dict(p) for p in recent.scalars().all()
        ]

        mem_count = await db.execute(
            select(func.count(NeuralMemory.id)).where(NeuralMemory.is_active.is_(True))
        )
        active_memories = mem_count.scalar() or 0

        last_training = None
        last_tr = await db.execute(
            select(NeuralTrainingHistory)
            .order_by(NeuralTrainingHistory.created_at.desc())
            .limit(1)
        )
        last_training_row = last_tr.scalar_one_or_none()
        if last_training_row:
            last_training = {
                "model_name": last_training_row.model_name,
                "model_version": last_training_row.model_version,
                "training_status": last_training_row.training_status,
                "accuracy": last_training_row.accuracy,
                "created_at": last_training_row.created_at,
            }

        return {
            "total_predictions": total_predictions,
            "by_type": by_type,
            "avg_confidence": avg_confidence,
            "recent_predictions": recent_predictions,
            "active_memories": active_memories,
            "last_training": last_training,
        }
