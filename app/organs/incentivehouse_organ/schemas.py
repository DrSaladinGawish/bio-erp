"""
Pydantic v2 Schemas — IncentiveHouse ERP Organ
===============================================

Mirrors the 27 ORM models in ``models.py`` plus the operational/master tables
the legacy migration pipeline depends on:

  *  6  Staging / audit (Bnk, Sal, Pur, Evn, Env + AuditLog)
  *  7  Pipeline lifecycle (ExtractionLog, ValidationLog, StagingLog,
                            ReconcileLog, ApprovalLog, PromotionLog, ObserveLog)
  *  2  Reconciliation (BnkReconciliation, BnkTrnxStaging)
  *  6  Master data      (Client, CostCenter, ChequeBook, SubLedgerKey,
                            TrnxKey, PnrRecord)
  *  6  Config / meta    (SourcePath, MappingRule, ValidationRule,
                            SnapshotRecord, ErrorLog, AgentRun)

All schemas use Pydantic v2 ``ConfigDict(from_attributes=True)`` so they
can be returned directly from SQLAlchemy ORM instances.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ════════════════════════════════════════════════════════════════════
#  1–6   Staging + Audit
# ════════════════════════════════════════════════════════════════════

class IncentiveHouseAuditLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    agent_id: str
    module: str
    source_file: Optional[str] = None
    total_rows: int = 0
    passed: int = 0
    warnings: int = 0
    failed: int = 0
    staged: int = 0
    dry_run: int = 1
    summary: Optional[str] = None
    errors_json: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class IncentiveHouseAuditLogCreate(IncentiveHouseAuditLogBase):
    pass


class IncentiveHouseAuditLogRead(IncentiveHouseAuditLogBase):
    id: int


class StagingRecordBase(BaseModel):
    """Common fields for the five *Staging tables (Bnk/Sal/Pur/Evn/Env)."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    agent_id: Optional[str] = None
    transaction_id: Optional[str] = None
    transaction_date: Optional[str] = None
    account_code: Optional[str] = None
    description: Optional[str] = None
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    currency: str = "EGP"
    exchange_rate: float = 1.0
    sub_led_code: Optional[int] = None
    pnr_id: Optional[int] = None
    client_id: Optional[int] = None
    cost_center: Optional[str] = None
    validation_status: str = "PASS"
    validation_errors: Optional[str] = None
    source_file: Optional[str] = None
    source_row: Optional[int] = None
    staged_at: Optional[str] = None


class BnkStagingCreate(StagingRecordBase):
    pass


class BnkStagingRead(StagingRecordBase):
    id: int


class SalStagingCreate(StagingRecordBase):
    pass


class SalStagingRead(StagingRecordBase):
    id: int


class PurStagingCreate(StagingRecordBase):
    pass


class PurStagingRead(StagingRecordBase):
    id: int


class EvnStagingCreate(StagingRecordBase):
    pass


class EvnStagingRead(StagingRecordBase):
    id: int


class EnvStagingCreate(StagingRecordBase):
    pass


class EnvStagingRead(StagingRecordBase):
    id: int


# ════════════════════════════════════════════════════════════════════
#  7–13  Pipeline lifecycle logs
# ════════════════════════════════════════════════════════════════════

class ExtractionLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    module: str
    source_file: Optional[str] = None
    user_id: Optional[str] = None
    status: Optional[str] = None
    extracted_at: Optional[str] = None


class ExtractionLogCreate(ExtractionLogBase):
    pass


class ExtractionLogRead(ExtractionLogBase):
    id: int
    created_at: Optional[str] = None


class ValidationLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    extract_id: int
    user_id: Optional[str] = None
    status: Optional[str] = None
    quality_score: float = 0.0
    validated_at: Optional[str] = None


class ValidationLogCreate(ValidationLogBase):
    pass


class ValidationLogRead(ValidationLogBase):
    id: int


class StagingLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    validate_id: int
    target_table: Optional[str] = None
    user_id: Optional[str] = None
    snapshot_id: Optional[str] = None
    status: Optional[str] = None
    staged_at: Optional[str] = None


class StagingLogCreate(StagingLogBase):
    pass


class StagingLogRead(StagingLogBase):
    id: int


class ReconcileLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    stage_id: int
    module: str
    user_id: Optional[str] = None
    status: Optional[str] = None
    total_records: int = 0
    reconciled_count: int = 0
    mismatch_count: int = 0
    unmatched_count: int = 0
    reconciled_at: Optional[str] = None


class ReconcileLogCreate(ReconcileLogBase):
    pass


class ReconcileLogRead(ReconcileLogBase):
    id: int


class ApprovalLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    recon_id: int
    approver_id: Optional[str] = None
    approval_level: Optional[str] = None
    status: Optional[str] = None
    approved_at: Optional[str] = None


class ApprovalLogCreate(ApprovalLogBase):
    pass


class ApprovalLogRead(ApprovalLogBase):
    id: int


class PromotionLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    approve_id: int
    user_id: Optional[str] = None
    rollback_token: Optional[str] = None
    status: Optional[str] = None
    promoted_at: Optional[str] = None


class PromotionLogCreate(PromotionLogBase):
    pass


class PromotionLogRead(PromotionLogBase):
    id: int


class ObserveLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    promote_id: int
    user_id: Optional[str] = None
    status: Optional[str] = None
    metrics: Optional[str] = None
    observed_at: Optional[str] = None


class ObserveLogCreate(ObserveLogBase):
    pass


class ObserveLogRead(ObserveLogBase):
    id: int


# ════════════════════════════════════════════════════════════════════
#  14–15 Reconciliation
# ════════════════════════════════════════════════════════════════════

class BnkReconciliationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    transaction_id: Optional[str] = None
    check_book_id: Optional[int] = None
    check_book_name: Optional[str] = None
    bank_amount: float = 0.0
    gl_amount: float = 0.0
    variance: float = 0.0
    recon_status: Optional[str] = "PENDING"
    user_sub_led: Optional[str] = None
    user_type: Optional[str] = None
    user_keyword: Optional[str] = None
    user_notes: Optional[str] = None


class BnkReconciliationCreate(BnkReconciliationBase):
    pass


class BnkReconciliationRead(BnkReconciliationBase):
    id: int


class BnkTrnxStagingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    transaction_id: Optional[str] = None
    check_book_id: Optional[str] = None
    transaction_date: Optional[str] = None
    narration: Optional[str] = None
    debit: float = 0.0
    credit: float = 0.0
    amount: float = 0.0
    currency: Optional[str] = "EGP"
    _extracted_at: Optional[str] = None
    _batch_id: Optional[str] = None
    _module: Optional[str] = None


class BnkTrnxStagingCreate(BnkTrnxStagingBase):
    pass


class BnkTrnxStagingRead(BnkTrnxStagingBase):
    id: int


# ════════════════════════════════════════════════════════════════════
#  16–21 Master data
# ════════════════════════════════════════════════════════════════════

class ClientBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    code: Optional[str] = None
    name: Optional[str] = None
    tax_id: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    acc_key: Optional[int] = None


class ClientCreate(ClientBase):
    pass


class ClientRead(ClientBase):
    id: int


class CostCenterBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    code: str
    name: Optional[str] = None
    type: Optional[str] = "PRODUCTION"
    parent_id: Optional[int] = None
    budget_limit: float = 0.0


class CostCenterCreate(CostCenterBase):
    pass


class CostCenterRead(CostCenterBase):
    id: int


class ChequeBookBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    bank_account_id: Optional[int] = None
    cheque_book_number: Optional[str] = None
    start_number: int = 0
    end_number: int = 0
    current_number: int = 0
    status: str = "ACTIVE"
    issue_date: Optional[str] = None
    branch_id: Optional[int] = None


class ChequeBookCreate(ChequeBookBase):
    pass


class ChequeBookRead(ChequeBookBase):
    id: int


class SubLedgerKeyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    sub_led_code: int
    description: Optional[str] = None
    account_code: Optional[str] = None
    active: int = 1


class SubLedgerKeyCreate(SubLedgerKeyBase):
    pass


class SubLedgerKeyRead(SubLedgerKeyBase):
    id: int


class TrnxKeyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    transaction_id: str
    transaction_type: Optional[str] = None
    module: Optional[str] = None
    description: Optional[str] = None


class TrnxKeyCreate(TrnxKeyBase):
    pass


class TrnxKeyRead(TrnxKeyBase):
    id: int


class PnrRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    pnr_code: str
    client_id: Optional[int] = None
    event_date: Optional[str] = None
    venue: Optional[str] = None
    status: Optional[str] = "OPEN"
    gross_sales: float = 0.0
    currency: str = "EGP"


class PnrRecordCreate(PnrRecordBase):
    pass


class PnrRecordRead(PnrRecordBase):
    id: int


# ════════════════════════════════════════════════════════════════════
#  22–27 Config / meta / operational
# ════════════════════════════════════════════════════════════════════

class SourcePathBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    module: str
    key: str
    path: str
    description: Optional[str] = None
    sheet: Optional[str] = None
    split_to: Optional[str] = None  # JSON list


class SourcePathCreate(SourcePathBase):
    pass


class SourcePathRead(SourcePathBase):
    id: int


class MappingRuleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    module: str
    source_column: str
    target_field: str
    transform: Optional[str] = None
    default_value: Optional[str] = None


class MappingRuleCreate(MappingRuleBase):
    pass


class MappingRuleRead(MappingRuleBase):
    id: int


class ValidationRuleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    module: str
    field: str
    rule_type: str  # required / range / regex / enum
    expression: Optional[str] = None
    severity: str = "ERROR"  # ERROR / WARN / INFO


class ValidationRuleCreate(ValidationRuleBase):
    pass


class ValidationRuleRead(ValidationRuleBase):
    id: int


class SnapshotRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    snapshot_id: str
    target_table: Optional[str] = None
    row_count: int = 0
    payload: Optional[str] = None  # JSON
    created_by: Optional[str] = "api"


class SnapshotRecordCreate(SnapshotRecordBase):
    pass


class SnapshotRecordRead(SnapshotRecordBase):
    id: int
    created_at: Optional[str] = None


class ErrorLogBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    batch_id: Optional[str] = None
    module: Optional[str] = None
    source_file: Optional[str] = None
    source_row: Optional[int] = None
    error_type: Optional[str] = None
    message: Optional[str] = None
    context: Optional[str] = None  # JSON


class ErrorLogCreate(ErrorLogBase):
    pass


class ErrorLogRead(ErrorLogBase):
    id: int
    created_at: Optional[str] = None


class AgentRunBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    agent_id: str
    module: str
    status: str = "ready"  # ready / running / success / failed
    last_run: Optional[str] = None
    payload: Optional[str] = None  # JSON


class AgentRunCreate(AgentRunBase):
    pass


class AgentRunRead(AgentRunBase):
    id: int
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


# ════════════════════════════════════════════════════════════════════
#  API request/response envelopes (used by routers)
# ════════════════════════════════════════════════════════════════════

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
    module: str = Field(default="all", pattern="^(Bnk|Sal|Pur|Evn|Env|all)$")
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


# ════════════════════════════════════════════════════════════════════
#  Reconciliation envelopes (used by recon_api.py / recon router)
# ════════════════════════════════════════════════════════════════════

class ReconStatusItem(BaseModel):
    recon_status: str
    count: int
    total_variance: float


class VarianceItem(BaseModel):
    check_book_id: int
    check_book_name: str
    transaction_id: str
    variance: float
    recon_status: str


class CheckBookSummary(BaseModel):
    cb_id: int
    name: str
    total: int
    ok: int
    bad: int


# ════════════════════════════════════════════════════════════════════
#  BNK Router schemas (used by bnk_router.py)
# ════════════════════════════════════════════════════════════════════

from datetime import date, datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class BNKTransactionCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    account_code: str = "Bnk_Cur"
    currency_code: str = "EGP"
    txn_date: date
    txn_type: str = "Debit"
    description: str = ""
    reference_no: str = ""
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    amount: float = 0.0
    sub_ledger_code: str | None = None
    pnr_id: int | None = None
    counterparty: str | None = None


class BNKTransactionOut(BNKTransactionCreate):
    id: int
    is_reconciled: bool = False
    is_flagged: bool = False
    source: str = "api"
    imported_at: datetime | None = None


class BNKTransactionList(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    id: int
    account_code: str
    txn_date: date | None = None
    description: str = ""
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    amount: float = 0.0
    txn_type: str = ""
    is_reconciled: bool = False


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    data: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 50
    pages: int = 0


class BNKAccountSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    account_code: str
    currency_code: str = "EGP"
    txn_count: int = 0
    total_debit: float = 0.0
    total_credit: float = 0.0
    net_balance: float = 0.0
    last_txn_date: date | None = None


class BNKDashboardSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    total_count: int = 0
    total_debit: float = 0.0
    total_credit: float = 0.0
    net_balance: float = 0.0
    reconciled_count: int = 0
    unreconciled_count: int = 0
    by_account: dict[str, int] = {}
    by_type: dict[str, int] = {}


class BNKReconciliationStatus(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    accounts: list[dict[str, Any]] = []
    total: int = 0
    matched: int = 0
    unmatched: int = 0
    flagged: int = 0
    match_rate: float = 0.0


# ════════════════════════════════════════════════════════════════════
#  Re-export everything for ``from app.organs.incentivehouse_organ.schemas import *``
# ════════════════════════════════════════════════════════════════════

__all__ = [
    # 1–6  Staging + audit
    "IncentiveHouseAuditLogBase", "IncentiveHouseAuditLogCreate", "IncentiveHouseAuditLogRead",
    "StagingRecordBase",
    "BnkStagingCreate", "BnkStagingRead",
    "SalStagingCreate", "SalStagingRead",
    "PurStagingCreate", "PurStagingRead",
    "EvnStagingCreate", "EvnStagingRead",
    "EnvStagingCreate", "EnvStagingRead",
    # 7–13 Lifecycle logs
    "ExtractionLogBase", "ExtractionLogCreate", "ExtractionLogRead",
    "ValidationLogBase", "ValidationLogCreate", "ValidationLogRead",
    "StagingLogBase", "StagingLogCreate", "StagingLogRead",
    "ReconcileLogBase", "ReconcileLogCreate", "ReconcileLogRead",
    "ApprovalLogBase", "ApprovalLogCreate", "ApprovalLogRead",
    "PromotionLogBase", "PromotionLogCreate", "PromotionLogRead",
    "ObserveLogBase", "ObserveLogCreate", "ObserveLogRead",
    # 14–15 Reconciliation
    "BnkReconciliationBase", "BnkReconciliationCreate", "BnkReconciliationRead",
    "BnkTrnxStagingBase", "BnkTrnxStagingCreate", "BnkTrnxStagingRead",
    # 16–21 Master data
    "ClientBase", "ClientCreate", "ClientRead",
    "CostCenterBase", "CostCenterCreate", "CostCenterRead",
    "ChequeBookBase", "ChequeBookCreate", "ChequeBookRead",
    "SubLedgerKeyBase", "SubLedgerKeyCreate", "SubLedgerKeyRead",
    "TrnxKeyBase", "TrnxKeyCreate", "TrnxKeyRead",
    "PnrRecordBase", "PnrRecordCreate", "PnrRecordRead",
    # 22–27 Config / meta
    "SourcePathBase", "SourcePathCreate", "SourcePathRead",
    "MappingRuleBase", "MappingRuleCreate", "MappingRuleRead",
    "ValidationRuleBase", "ValidationRuleCreate", "ValidationRuleRead",
    "SnapshotRecordBase", "SnapshotRecordCreate", "SnapshotRecordRead",
    "ErrorLogBase", "ErrorLogCreate", "ErrorLogRead",
    "AgentRunBase", "AgentRunCreate", "AgentRunRead",
    # API envelopes
    "ExtractionRequest", "ModuleExtractionResult", "ExtractionResponse",
    "StagingQuery", "StagingRecord", "StagingListResponse",
    "PromoteRequest", "PromoteResponse",
    "AgentStatusResponse", "SourceFileInfo", "SourceListResponse",
    "ReconStatusItem", "VarianceItem", "CheckBookSummary",
]
