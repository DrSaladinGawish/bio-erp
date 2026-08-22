"""
Library Compliance Checker (LCC) ORM Models
Part of ERP Builder Agent (EBA) v1.0
BIO-ERP — SQLAlchemy Models
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class LibraryComplianceScan(Base):
    __tablename__ = "library_compliance_scans"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(String(50), unique=True, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    scope = Column(JSON, default=list)  # ["python", "nodejs", "docker", "system"]
    total_packages = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    high_count = Column(Integer, default=0)
    medium_count = Column(Integer, default=0)
    low_count = Column(Integer, default=0)
    pass_count = Column(Integer, default=0)
    compliance_score = Column(Float, default=0.0)
    findings = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    status = Column(String(20), default="pending")  # pending, running, pass, warn, fail
    triggered_by = Column(String(50), default="scheduled")  # scheduled, manual, webhook
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)


class LibraryWhitelist(Base):
    __tablename__ = "library_whitelist"

    id = Column(Integer, primary_key=True, index=True)
    package_name = Column(String(100), index=True, nullable=False)
    version_constraint = Column(String(50), default=">=0.0.0")
    reason = Column(Text, nullable=False)
    added_by = Column(String(100), nullable=False)
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
