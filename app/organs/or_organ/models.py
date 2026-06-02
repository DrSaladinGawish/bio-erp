import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class OrPrescription(Base):
    __tablename__ = "or_prescriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(255), nullable=False, index=True)
    patient_name = Column(String(255), nullable=False)
    patient_id = Column(String(255), nullable=False)
    medication = Column(String(255), nullable=False)
    dosage = Column(String(255), nullable=False)
    prescribing_doctor = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    issued_at = Column(String(64), nullable=True)
    status = Column(String(32), default="pending")
    exported = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
