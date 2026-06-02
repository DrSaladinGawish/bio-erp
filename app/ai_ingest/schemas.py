from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class NeuralNodeOut(BaseModel):
    id: int
    label: str
    node_type: str
    description: str | None = None
    confidence: float = 0.0
    metadata_json: dict | None = None

    class Config:
        from_attributes = True


class NeuralLinkOut(BaseModel):
    id: int
    source_node_id: int
    target_node_id: int
    link_type: str
    weight: float = 1.0

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    message: str = ""


class AnalysisResult(BaseModel):
    id: int
    document_id: int
    status: str
    raw_text: str | None = None
    extracted_entities: dict | None = None
    extracted_patterns: list | None = None
    neural_nodes: list | None = None
    neural_links: list | None = None
    summary: str | None = None
    confidence_score: float = 0.0
    processing_time_ms: int | None = None

    class Config:
        from_attributes = True


class JournalLine(BaseModel):
    coa_account_id: int
    coa_account_name: str = ""
    debit: float = 0.0
    credit: float = 0.0
    description: str | None = None


class SuggestedTransactionOut(BaseModel):
    id: int
    document_id: int
    analysis_id: int | None = None
    transaction_type: str
    title: str | None = None
    description: str | None = None
    journal_lines: list[JournalLine] | list | None = None
    total_debit: float = 0.0
    total_credit: float = 0.0
    confidence_score: float = 0.0
    status: str = "draft"
    review_notes: str | None = None

    class Config:
        from_attributes = True


class ReviewRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|amend|reject)$")
    notes: str | None = None
    journal_lines: list[JournalLine] | None = None


class PatternLogOut(BaseModel):
    id: int
    pattern_type: str
    pattern_key: str
    pattern_value: str | None = None
    matched_entities: list | None = None
    confidence: float = 0.0
    source: str = "local"

    class Config:
        from_attributes = True


class IngestionStatusOut(BaseModel):
    document_id: int
    filename: str
    upload_status: str
    analysis_status: str | None = None
    suggestion_status: str | None = None
    posted_jv_id: int | None = None


class ProtocolResult(BaseModel):
    success: bool
    gate: str
    message: str
    data: Any = None
    error: str | None = None
