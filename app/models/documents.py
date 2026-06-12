"""
Document Management System — SQLAlchemy Models
Drop into app/models/documents.py or append to existing models.py
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    BigInteger,
    DateTime,
    Index,
    PrimaryKeyConstraint,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.database import Base  # Adjust import to your project


class SupportingDocument(Base):
    """Universal supporting document for any transaction."""

    __tablename__ = "supporting_documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_name = Column(String(32), nullable=False, index=True)
    function_name = Column(String(32), nullable=False, index=True)
    transaction_table = Column(String(64), nullable=False, index=True)
    transaction_id = Column(String(64), nullable=False, index=True)
    original_usb_path = Column(Text)
    archive_path = Column(Text, nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False, index=True)
    file_size_bytes = Column(BigInteger, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_ext = Column(String(10), nullable=False)
    ingested_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    status = Column(String(16), default="linked", nullable=False)
    uploaded_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('linked', 'verified', 'missing', 'modified')",
            name="ck_doc_status",
        ),
        Index("idx_docs_composite", "module_name", "function_name", "status"),
    )

    def __repr__(self):
        return f"<SupportingDocument {self.module_name}/{self.function_name}: {self.file_name}>"


class DocumentModule(Base):
    """Lookup table: which module/function maps to which transaction table."""

    __tablename__ = "document_modules"

    module_name = Column(String(32), nullable=False)
    function_name = Column(String(32), nullable=False)
    transaction_table = Column(String(64), nullable=False)
    description = Column(Text)
    filename_pattern = Column(String(255))

    __table_args__ = (PrimaryKeyConstraint("module_name", "function_name"),)

    def __repr__(self):
        return f"<DocumentModule {self.module_name}.{self.function_name} → {self.transaction_table}>"
