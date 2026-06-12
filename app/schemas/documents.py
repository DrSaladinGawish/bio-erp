"""
Document Management System — Pydantic v2 Schemas
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# ── Shared ──────────────────────────────────────────
class DocumentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Request Schemas ───────────────────────────────────
class IngestRequest(BaseModel):
    usb_drive_letter: str = Field(default="D", pattern=r"^[A-Z]$")
    usb_base_path: str = Field(default="flash memory\\USB Drive")
    modules: List[str] = Field(default_factory=list)
    auto_link: bool = True
    copy_to_archive: bool = True
    compute_hash: bool = True


class VerifyRequest(BaseModel):
    module_name: Optional[str] = None
    function_name: Optional[str] = None
    transaction_table: Optional[str] = None


class LinkRequest(BaseModel):
    document_id: UUID
    transaction_table: str
    transaction_id: str


# ── Response Schemas ──────────────────────────────────
class IngestResultItem(BaseModel):
    file: str
    status: str  # linked, orphaned, error
    reason: Optional[str] = None
    transaction_id: Optional[str] = None
    archive_path: Optional[str] = None
    file_hash: Optional[str] = None


class IngestResponse(BaseModel):
    total_files_found: int
    ingested: int
    linked: int
    orphaned: int
    errors: int
    bytes_copied: int
    manifest: List[IngestResultItem]


class DocumentOut(DocumentBase):
    id: UUID
    module_name: str
    function_name: str
    transaction_table: str
    transaction_id: str
    original_usb_path: Optional[str] = None
    archive_path: str
    file_hash_sha256: str
    file_size_bytes: int
    file_name: str
    file_ext: str
    ingested_at: datetime
    verified_at: Optional[datetime] = None
    status: str
    uploaded_by: Optional[str] = None


class DocumentListResponse(BaseModel):
    total: int
    items: List[DocumentOut]


class VerifyResult(BaseModel):
    total_checked: int
    verified: int
    modified: int
    missing: int
    errors: int


class DocumentModuleOut(DocumentBase):
    module_name: str
    function_name: str
    transaction_table: str
    description: Optional[str]
    filename_pattern: Optional[str]


class DocumentModuleList(BaseModel):
    modules: List[DocumentModuleOut]
