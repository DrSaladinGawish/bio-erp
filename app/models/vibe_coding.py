"""
Vibe Coding Agent (VCA) ORM Models
Part of ERP Builder Agent (EBA) v1.0
BIO-ERP — SQLAlchemy Models
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Float, Boolean
from sqlalchemy.sql import func
from app.database import Base


class VibeCodingSession(Base):
    __tablename__ = "vibe_coding_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), unique=True, index=True, nullable=False)
    prompt = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    target_module = Column(String(50), default="general")
    status = Column(String(20), default="queued")
    generated_files = Column(JSON, default=list)
    test_results = Column(JSON, nullable=True)
    lint_results = Column(JSON, nullable=True)
    git_branch = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String(100), nullable=True)
    approval_notes = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    duration_seconds = Column(Integer, nullable=True)


class VibeCodeTemplate(Base):
    __tablename__ = "vibe_code_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    template_code = Column(Text, nullable=False)
    module_type = Column(String(50), nullable=False)
    target_organ = Column(String(50), default="general")
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
