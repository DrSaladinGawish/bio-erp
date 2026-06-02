"""
Pydantic schemas for IncentiveHouse ERP Organ API.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExtractionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    file_path: str = Field(..., description="Full path to Excel source file")
    module: str = Field(..., pattern="^(Bnk|Sal|Pur|Evn|Env|GL)$")
    sheet_name: Optional[str] = Field(None, description="Excel sheet name (auto-detect if null)")
    header_row: Optional[int] = Field(None, description="Header row index 0-based")
    batch_size: int = Field(default=500, ge=1, le=5000)
    dry_run: bool = Field(default=True, description="Validate only, skip staging write")


class ModuleExtractionResult(BaseModel):
    agent_id: str
    module: str
    source_file: str
    total_rows: int
    passed: int
    warnings: int
    failed: int
    staged: int
    summary: str
    errors: list = []
    started_at: str
    completed_at: str = ""


class ExtractionResponse(BaseModel):
    batch_id: str = ""
    results: list[ModuleExtractionResult] = []
    total_rows: int = 0
    total_staged: int = 0
    total_passed: int = 0
    total_warnings: int = 0
    total_failed: int = 0
    dry_run: bool = True
    timestamp: str = ""


class StagingQuery(BaseModel):
    model_config = ConfigDict(extra="ignore")

    module: str = Field(default="", pattern="^(Bnk|Sal|Pur|Evn|Env|all)$")
    status: str = Field(default="", pattern="^(PASS|WARN|FAIL|)$")
    limit: int = Field(default=100, ge=1, le=5000)
    offset: int = Field(default=0, ge=0)


class StagingRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    transaction_id: str
    transaction_date: str = ""
    account_code: str = ""
    description: str = ""
    debit_amount: float = 0
    credit_amount: float = 0
    currency: str = "EGP"
    sub_led_code: int = 0
    pnr_id: int = 0
    client_id: int = 0
    validation_status: str = "PASS"
    validation_errors: list = []
    staged_at: str = ""


class StagingListResponse(BaseModel):
    module: str
    total: int
    records: list[StagingRecord] = []


class PromoteRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    module: str = Field(..., pattern="^(Bnk|Sal|Pur|Evn|Env)$")
    record_ids: Optional[list[int]] = Field(None, description="Specific IDs to promote (null = all PASS)")
    confirmed: bool = Field(False, description="Must be True to actually promote")


class PromoteResponse(BaseModel):
    module: str
    promoted: int = 0
    requested: int = 0
    skipped: int = 0
    table_from: str = ""
    table_to: str = ""
    confirmation_required: bool = True
    message: str = ""


class AgentStatusResponse(BaseModel):
    agent_id: str
    status: str = "idle"
    last_run: Optional[dict] = None
    uptime: str = ""


class SourceFileInfo(BaseModel):
    key: str
    path: str
    description: str = ""
    sheet: Optional[str] = None
    split_to: list[str] = []


class SourceListResponse(BaseModel):
    sources: list[SourceFileInfo] = []
