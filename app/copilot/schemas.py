from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

class ConfidenceLevel(BaseModel):
    score: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence 0-1")
    label: Literal["low", "medium", "high", "very_high"] = "medium"
    source: str = "rule-based"

class Suggestion(BaseModel):
    id: str = ""
    type: str = "info"
    title: str = ""
    description: str = ""
    action: Optional[str] = None
    confidence: ConfidenceLevel = ConfidenceLevel()
    data: Optional[Dict[str, Any]] = None

class Pattern(BaseModel):
    id: str = ""
    name: str = ""
    field: str = ""
    match_type: str = "exact"
    pattern: str = ""
    confidence: float = 0.5
    occurrences: int = 0
    last_seen: Optional[str] = None

class EventAnalysisRequest(BaseModel):
    event_name: Optional[str] = None
    client_name: Optional[str] = None
    event_type: Optional[str] = None
    budget: Optional[float] = None
    guest_count: Optional[int] = None
    venue: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class EventLineItem(BaseModel):
    name: str = ""
    estimated_cost: float = 0.0
    category: str = "general"

class EventAnalysisResponse(BaseModel):
    event_name: str = ""
    event_type: str = "corporate"
    estimated_budget: float = 0.0
    budget_range: Dict[str, float] = {"min": 0, "max": 0, "recommended": 0}
    suggested_vendors: List[Dict[str, Any]] = []
    suggested_staff: List[Dict[str, Any]] = []
    suggestions: List[Suggestion] = []
    risks: List[str] = []
    confidence: ConfidenceLevel = ConfidenceLevel()

class POGenerateRequest(BaseModel):
    event_id: Optional[int] = None
    event_name: Optional[str] = None
    supplier_name: Optional[str] = None
    line_items: Optional[List[Dict[str, Any]]] = None
    budget_remaining: Optional[float] = None
    urgent: bool = False

class POLineItem(BaseModel):
    name: str = ""
    quantity: int = 1
    unit: str = "each"
    rate: float = 0.0
    total: float = 0.0
    category: str = "general"

class POGenerateResponse(BaseModel):
    po_lines: List[Dict[str, Any]] = []
    total_amount: float = 0.0
    budget_status: str = "ok"
    budget_remaining_after: Optional[float] = None
    supplier_score: Optional[float] = None
    duplicate_warnings: List[str] = []
    suggestions: List[Suggestion] = []
    confidence: ConfidenceLevel = ConfidenceLevel()

class ReconRequest(BaseModel):
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    auto_match_threshold: float = 0.85
    learn_from_batch: bool = True

class ReconResponse(BaseModel):
    matched: List[Dict[str, Any]] = []
    unmatched: List[Dict[str, Any]] = []
    suspicious: List[Dict[str, Any]] = []
    stats: Dict[str, Any] = {"total": 0, "matched": 0, "unmatched": 0, "suspicious": 0}
    suggestions: List[Suggestion] = []
    confidence: ConfidenceLevel = ConfidenceLevel()

class FinancialSummary(BaseModel):
    period: str = ""
    revenue: float = 0.0
    costs: float = 0.0
    gross_profit: float = 0.0
    margin_pct: float = 0.0
    cash_position: float = 0.0
    cash_projected_30d: Optional[float] = None
    cash_projected_60d: Optional[float] = None
    budget_used_pct: float = 0.0
    budget_total: float = 0.0
    budget_remaining: float = 0.0
    alerts: List[Dict[str, Any]] = []
    insights: List[str] = []
    trends: Dict[str, Any] = {}

class FinancialAlert(BaseModel):
    severity: Literal["red", "yellow", "green"] = "green"
    title: str = ""
    description: str = ""
    module: str = ""
    action_url: Optional[str] = None

class PanelRequest(BaseModel):
    form_type: Literal["event", "po", "recon", "financial", "dashboard"] = "dashboard"
    form_data: Optional[Dict[str, Any]] = None
    entity_id: Optional[str] = None

class PanelResponse(BaseModel):
    form_type: str = "dashboard"
    context_title: str = ""
    suggestions: List[Suggestion] = []
    quick_actions: List[Dict[str, str]] = []
    summary: str = ""
    engine_status: str = "ready"

class CoPilotAskRequest(BaseModel):
    question: str = ""
    context: Optional[Dict[str, Any]] = None

class CoPilotAskResponse(BaseModel):
    answer: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel()
    sources: List[str] = []
    follow_up_questions: List[str] = []
