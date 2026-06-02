from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
import enum


class NodeType(str, enum.Enum):
    entity = "entity"
    concept = "concept"
    pattern = "pattern"
    rule = "rule"
    template = "template"


class LinkType(str, enum.Enum):
    relates_to = "relates_to"
    is_a = "is_a"
    part_of = "part_of"
    triggers = "triggers"
    suggests = "suggests"


class AnalysisStatus(str, enum.Enum):
    pending = "pending"
    analyzing = "analyzing"
    completed = "completed"
    failed = "failed"


class SuggestionStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    approved = "approved"
    amended = "amended"
    rejected = "rejected"
    posted = "posted"


class SurgeryStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    committed = "committed"
    rolled_back = "rolled_back"
    failed = "failed"


class NeuralNode(Base):
    __tablename__ = "neural_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    label: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    node_type: Mapped[str] = mapped_column(SAEnum(NodeType), nullable=False, default=NodeType.entity)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    source_document_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_document_ingestion.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    outgoing_links = relationship("NeuralLink", foreign_keys="NeuralLink.source_node_id", back_populates="source_node")
    incoming_links = relationship("NeuralLink", foreign_keys="NeuralLink.target_node_id", back_populates="target_node")


class NeuralLink(Base):
    __tablename__ = "neural_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source_node_id: Mapped[int] = mapped_column(Integer, ForeignKey("neural_nodes.id"), nullable=False)
    target_node_id: Mapped[int] = mapped_column(Integer, ForeignKey("neural_nodes.id"), nullable=False)
    link_type: Mapped[str] = mapped_column(SAEnum(LinkType), nullable=False, default=LinkType.relates_to)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)

    source_node = relationship("NeuralNode", foreign_keys=[source_node_id], back_populates="outgoing_links")
    target_node = relationship("NeuralNode", foreign_keys=[target_node_id], back_populates="incoming_links")


class AIDocumentIngestion(Base):
    __tablename__ = "ai_document_ingestion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=True)
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="uploaded")
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    analysis_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_document_analysis.id"), nullable=True)
    archive_path: Mapped[str] = mapped_column(String(1000), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)


class AIDocumentAnalysis(Base):
    __tablename__ = "ai_document_analysis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_document_ingestion.id"), nullable=False)
    status: Mapped[str] = mapped_column(SAEnum(AnalysisStatus), default=AnalysisStatus.pending)
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)
    extracted_entities: Mapped[dict] = mapped_column(JSON, nullable=True)
    extracted_patterns: Mapped[list] = mapped_column(JSON, nullable=True)
    neural_nodes: Mapped[list] = mapped_column(JSON, nullable=True)
    neural_links: Mapped[list] = mapped_column(JSON, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=True)


class AISuggestedTransaction(Base):
    __tablename__ = "ai_suggested_transaction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_document_ingestion.id"), nullable=False)
    analysis_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_document_analysis.id"), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    journal_lines: Mapped[list] = mapped_column(JSON, nullable=False)
    total_debit: Mapped[float] = mapped_column(Float, default=0.0)
    total_credit: Mapped[float] = mapped_column(Float, default=0.0)
    currency_id: Mapped[int] = mapped_column(Integer, ForeignKey("currencies.id"), nullable=True)
    branch_id: Mapped[int] = mapped_column(Integer, ForeignKey("branches.id"), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(SAEnum(SuggestionStatus), default=SuggestionStatus.draft)
    review_notes: Mapped[str] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    posted_jv_id: Mapped[int] = mapped_column(Integer, ForeignKey("jv_headers.id"), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)


class AINeuralPatternLog(Base):
    __tablename__ = "ai_neural_pattern_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_document_ingestion.id"), nullable=True)
    analysis_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_document_analysis.id"), nullable=True)
    pattern_type: Mapped[str] = mapped_column(String(100), nullable=False)
    pattern_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    pattern_value: Mapped[str] = mapped_column(Text, nullable=True)
    matched_entities: Mapped[list] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(50), default="local")


class SurgeryAuditLog(Base):
    __tablename__ = "surgery_audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    surgery_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    protocol: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(SAEnum(SurgeryStatus), default=SurgeryStatus.pending)
    table_name: Mapped[str] = mapped_column(String(100), nullable=True)
    record_id: Mapped[int] = mapped_column(Integer, nullable=True)
    snapshot_before: Mapped[dict] = mapped_column(JSON, nullable=True)
    snapshot_after: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    performed_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=True)
