from datetime import datetime
from sqlalchemy import Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import BaseMixin, _utcnow


class NeuralPrediction(Base, BaseMixin):
    __tablename__ = "neural_predictions"
    prediction_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="cash_flow, client_churn, pnr_overrun, transaction_anomaly")
    prediction_key: Mapped[str] = mapped_column(String(255), nullable=False)
    predicted_value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    actual_value: Mapped[float] = mapped_column(Float, nullable=True)
    features_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=True)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    prediction_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=True)


class NeuralFeatureStore(Base, BaseMixin):
    __tablename__ = "neural_feature_store"
    feature_group: Mapped[str] = mapped_column(String(50), nullable=False)
    feature_key: Mapped[str] = mapped_column(String(255), nullable=False)
    feature_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    feature_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    valid_to: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class NeuralTrainingHistory(Base, BaseMixin):
    __tablename__ = "neural_training_history"
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    training_type: Mapped[str] = mapped_column(String(50), nullable=False, default="full")
    training_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    dataset_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy: Mapped[float] = mapped_column(Float, nullable=True)
    loss: Mapped[float] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=True)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=True)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)


class NeuralMemory(Base, BaseMixin):
    __tablename__ = "neural_memory"
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="conversation, insight, pattern, feedback")
    memory_key: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[dict] = mapped_column(JSONB, nullable=True)
    importance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
