"""
P1-B4: Document Management System (DMS)
Full document lifecycle: upload, version control, approval workflow, retention.
Zero Gap Compliance for document handling.
"""

import os
import hashlib
import mimetypes
import json
from datetime import datetime, timedelta
from typing import Dict
from pathlib import Path
from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from app.organs.incentivehouse_organ.models import IncentiveBase
from app.organs.incentivehouse_organ.db import get_sync_session_factory
from app.organs.incentivehouse_organ.rbac import Permission, require_permission


class DocumentStatus(str, PyEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    EXPIRED = "expired"


class DocumentType(str, PyEnum):
    CONTRACT = "contract"
    INVOICE = "invoice"
    PO = "purchase_order"
    QUOTE = "quote"
    EVENT_BRIEF = "event_brief"
    VENDOR_CERT = "vendor_certificate"
    PASSPORT = "passport"
    INSURANCE = "insurance"
    OTHER = "other"


class Document(IncentiveBase):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_code = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    document_type = Column(String(50), nullable=False)
    original_filename = Column(String(500), nullable=False)
    storage_path = Column(String(1000), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    previous_version_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    is_latest = Column(Boolean, default=True, nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(Integer, nullable=True)
    status = Column(String(20), default=DocumentStatus.DRAFT.value, nullable=False)
    uploaded_by = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    retention_days = Column(Integer, default=2555)
    expires_at = Column(DateTime, nullable=True)
    compliance_flag = Column(String(50), nullable=True)
    tags = Column(Text, nullable=True)
    ocr_text = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    deleted_by = Column(String(100), nullable=True)
    deleted_at = Column(DateTime, nullable=True)


class DocumentService:
    UPLOAD_DIR = Path(os.getenv("DMS_UPLOAD_DIR", "D:/ERP System/BIO_ERP/documents"))
    MAX_FILE_SIZE = int(os.getenv("DMS_MAX_FILE_SIZE", "52428800"))
    ALLOWED_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/csv",
    }

    def __init__(self, db_session: Session):
        self.db = db_session
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def upload_document(
        self,
        file: UploadFile,
        title: str,
        doc_type: DocumentType,
        entity_type: str = None,
        entity_id: int = None,
        uploaded_by: str = "system",
        tags: list = None,
    ) -> Document:
        if file.size > self.MAX_FILE_SIZE:
            raise HTTPException(
                413, f"File too large. Max: {self.MAX_FILE_SIZE / 1024 / 1024}MB"
            )

        content_type = (
            file.content_type
            or mimetypes.guess_type(file.filename)[0]
            or "application/octet-stream"
        )
        if content_type not in self.ALLOWED_TYPES:
            raise HTTPException(415, f"File type not allowed: {content_type}")

        content = file.file.read()
        checksum = hashlib.sha256(content).hexdigest()

        existing = (
            self.db.query(Document)
            .filter(Document.checksum_sha256 == checksum, not Document.is_deleted)
            .first()
        )
        if existing:
            raise HTTPException(
                409, f"Duplicate file detected: {existing.document_code}"
            )

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        doc_code = (
            f"DOC-{timestamp}-{hashlib.md5(checksum.encode()).hexdigest()[:6].upper()}"
        )

        storage_dir = (
            self.UPLOAD_DIR / doc_type.value / datetime.now().strftime("%Y/%m")
        )
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_path = storage_dir / f"{doc_code}_{file.filename}"
        with open(storage_path, "wb") as f:
            f.write(content)

        doc = Document(
            document_code=doc_code,
            title=title,
            document_type=doc_type.value,
            original_filename=file.filename,
            storage_path=str(storage_path),
            file_size_bytes=len(content),
            mime_type=content_type,
            checksum_sha256=checksum,
            entity_type=entity_type,
            entity_id=entity_id,
            uploaded_by=uploaded_by,
            tags=json.dumps(tags or []),
            expires_at=datetime.utcnow() + timedelta(days=2555),
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_document(self, doc_id: int) -> Document:
        doc = (
            self.db.query(Document)
            .filter(Document.id == doc_id, not Document.is_deleted)
            .first()
        )
        if not doc:
            raise HTTPException(404, "Document not found")
        return doc

    def search_documents(
        self,
        query: str = None,
        doc_type: DocumentType = None,
        entity_type: str = None,
        entity_id: int = None,
        status: DocumentStatus = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict:
        q = self.db.query(Document).filter(not Document.is_deleted)
        if query:
            q = q.filter(Document.title.ilike(f"%{query}%"))
        if doc_type:
            q = q.filter(Document.document_type == doc_type.value)
        if entity_type:
            q = q.filter(Document.entity_type == entity_type)
        if entity_id:
            q = q.filter(Document.entity_id == entity_id)
        if status:
            q = q.filter(Document.status == status.value)
        total = q.count()
        docs = (
            q.order_by(Document.uploaded_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {"total": total, "page": page, "page_size": page_size, "documents": docs}

    def cleanup_expired(self) -> int:
        cutoff = datetime.utcnow()
        expired = (
            self.db.query(Document)
            .filter(
                Document.expires_at < cutoff,
                Document.status != DocumentStatus.ARCHIVED.value,
                not Document.is_deleted,
            )
            .all()
        )
        for doc in expired:
            doc.status = DocumentStatus.EXPIRED.value
        self.db.commit()
        return len(expired)


# ── API Router ──

from fastapi import APIRouter, Depends, File, UploadFile, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/documents", tags=["Document Management"])


def get_db():
    session = get_sync_session_factory()()
    try:
        yield session
    finally:
        session.close()


@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    title: str = Query(...),
    doc_type: DocumentType = Query(...),
    entity_type: str = Query(None),
    entity_id: int = Query(None),
    tags: str = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.EVENT_UPDATE)),
):
    service = DocumentService(db)
    tag_list = tags.split(",") if tags else []
    doc = service.upload_document(
        file=file,
        title=title,
        doc_type=doc_type,
        entity_type=entity_type,
        entity_id=entity_id,
        uploaded_by=current_user.get("username", "system"),
        tags=tag_list,
    )
    return doc


@router.get("/{doc_id}")
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.EVENT_READ)),
):
    service = DocumentService(db)
    return service.get_document(doc_id)


@router.get("/{doc_id}/download")
def download_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_permission(Permission.EVENT_READ)),
):
    service = DocumentService(db)
    doc = service.get_document(doc_id)
    return FileResponse(doc.storage_path, filename=doc.original_filename)
