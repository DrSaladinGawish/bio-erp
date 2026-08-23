from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PredictionCreate(BaseModel):
    prediction_type: str = Field(
        ..., pattern=r"^(cash_flow|client_churn|pnr_overrun|transaction_anomaly)$"
    )
    prediction_key: str
    predicted_value: float
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    features_snapshot: dict[str, Any] | None = None
    model_version: str = "1.0.0"
    metadata_json: dict[str, Any] | None = None


class PredictionResponse(PredictionCreate):
    id: int
    actual_value: float | None = None
    prediction_date: datetime
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class FeatureStoreCreate(BaseModel):
    feature_group: str
    feature_key: str
    feature_data: dict[str, Any]
    feature_version: str = "1.0.0"
    valid_to: datetime | None = None


class FeatureStoreResponse(FeatureStoreCreate):
    id: int
    valid_from: datetime
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class TrainingCreate(BaseModel):
    model_name: str
    model_version: str = "1.0.0"
    training_type: str = Field(
        default="full", pattern=r"^(full|incremental|cross_validation)$"
    )
    dataset_size: int = 0
    parameters: dict[str, Any] | None = None


class TrainingResponse(TrainingCreate):
    id: int
    training_status: str
    accuracy: float | None = None
    loss: float | None = None
    duration_seconds: float | None = None
    metrics: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class MemoryCreate(BaseModel):
    memory_type: str = Field(..., pattern=r"^(conversation|insight|pattern|feedback)$")
    memory_key: str
    content: str
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata_json: dict[str, Any] | None = None
    user_id: int | None = None
    expires_at: datetime | None = None


class MemoryResponse(MemoryCreate):
    id: int
    embedding: dict[str, Any] | None = None
    access_count: int = 0
    last_accessed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class PredictionRequest(BaseModel):
    # Includes the ANN-backed predictor types (financial_ann,
    # revenue_forecast, anomaly_detector). churn_classifier stays
    # excluded even though trained_models/client_churn.pt now exists:
    # that checkpoint was trained on synthetic demo data
    # (scripts/seed_demo_clients.py, training_data="demo/synthetic"
    # in its checkpoint metadata). It may only be opened after a
    # retrain against REAL client churn outcomes.
    prediction_type: str = Field(
        ...,
        pattern=r"^(cash_flow|client_churn|pnr_overrun|transaction_anomaly"
                r"|financial_ann|revenue_forecast|anomaly_detector)$",
    )
    entity_id: str
    context: dict[str, Any] | None = None


class HumanFeedback(BaseModel):
    prediction_id: int
    actual_value: float
    feedback_notes: str | None = None


class DashboardInsight(BaseModel):
    total_predictions: int
    by_type: dict[str, int]
    avg_confidence: float
    recent_predictions: list[PredictionResponse]
    active_memories: int
    last_training: TrainingResponse | None


class PaginatedResponse(BaseModel):
    data: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
