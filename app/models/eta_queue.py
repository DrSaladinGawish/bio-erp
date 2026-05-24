from sqlalchemy import Column, Integer, String, Text, DateTime, SmallInteger
from datetime import timezone, datetime, timezone
from app.database import Base


class ETASubmissionQueue(Base):
    __tablename__ = "eta_submission_queue"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)
    internal_id = Column(String(100), unique=True, nullable=False, index=True)
    document_json = Column(Text, nullable=False)
    status = Column(
        String(20), default="pending", index=True
    )  # pending, submitted, accepted, rejected, retrying, failed
    retry_count = Column(SmallInteger, default=0)
    max_retries = Column(SmallInteger, default=5)
    last_error = Column(Text, nullable=True)
    eta_uuid = Column(String(100), nullable=True, index=True)
    eta_long_id = Column(String(200), nullable=True)
    rejection_code = Column(String(20), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    submission_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    submitted_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
