"""
Co-Pilot Router — 19 FastAPI endpoints for all smart modules.
Mount at /api/v1/copilot in your main app.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Optional

from .engine import CoPilotEngine
from .schemas import (
    EventAnalysisRequest, EventAnalysisResponse,
    POGenerateRequest, POGenerateResponse,
    ReconRequest, ReconResponse,
    FinancialSummary,
    PanelRequest, PanelResponse,
    CoPilotAskRequest, CoPilotAskResponse,
    Suggestion, ConfidenceLevel,
)
from .event_assistant import EventAssistant
from .po_assistant import POAssistant
from .recon_assistant import ReconAssistant
from .financial_cockpit import FinancialCockpit
from .notifications import NotificationEngine

router = APIRouter(prefix="/copilot", tags=["Co-Pilot"])

# ── Shared engine instance ──────────────────────────────────────────────────
_engine: Optional[CoPilotEngine] = None
_event_assistant: Optional[EventAssistant] = None
_po_assistant: Optional[POAssistant] = None
_recon_assistant: Optional[ReconAssistant] = None
_financial_cockpit: Optional[FinancialCockpit] = None
_notifications: Optional[NotificationEngine] = None


def get_engine() -> CoPilotEngine:
    global _engine
    if _engine is None:
        _engine = CoPilotEngine()
    return _engine


def get_event_assistant() -> EventAssistant:
    global _event_assistant
    if _event_assistant is None:
        _event_assistant = EventAssistant(get_engine())
    return _event_assistant


def get_po_assistant() -> POAssistant:
    global _po_assistant
    if _po_assistant is None:
        _po_assistant = POAssistant(get_engine())
    return _po_assistant


def get_recon_assistant() -> ReconAssistant:
    global _recon_assistant
    if _recon_assistant is None:
        _recon_assistant = ReconAssistant(get_engine())
    return _recon_assistant


def get_financial_cockpit() -> FinancialCockpit:
    global _financial_cockpit
    if _financial_cockpit is None:
        _financial_cockpit = FinancialCockpit(get_engine())
    return _financial_cockpit


def get_notifications() -> NotificationEngine:
    global _notifications
    if _notifications is None:
        _notifications = NotificationEngine(get_engine())
    return _notifications


# ══════════════════════════════════════════════════════════════════════════
# HEALTH & STATUS
# ══════════════════════════════════════════════════════════════════════════

@router.get("/health", summary="Co-Pilot health check")
async def copilot_health():
    engine = get_engine()
    return {"status": "ok", "engine": engine.health()}


@router.get("/status", summary="Co-Pilot engine status")
async def copilot_status():
    engine = get_engine()
    return {
        "version": "1.0.0",
        "status": "ready",
        "modules": {
            "event_assistant": True,
            "po_assistant": True,
            "recon_assistant": True,
            "financial_cockpit": True,
            "notifications": True,
        },
        "patterns_learned": engine.pattern_count(),
        "engine": engine.health(),
    }


# ══════════════════════════════════════════════════════════════════════════
# MODULE A: SMART EVENT BUILDER
# ══════════════════════════════════════════════════════════════════════════

@router.post("/event/analyze", response_model=EventAnalysisResponse,
             summary="Full event analysis with budget, vendors, staff")
async def event_analyze(request: EventAnalysisRequest):
    assistant = get_event_assistant()
    return assistant.analyze(request)


@router.post("/event/templates", summary="Get event templates")
async def event_templates(event_type: Optional[str] = None):
    from .event_assistant import EVENT_TEMPLATES
    if event_type:
        tmpl = EVENT_TEMPLATES.get(event_type)
        if not tmpl:
            raise HTTPException(404, f"Template '{event_type}' not found")
        return {"template": tmpl}
    return {"templates": list(EVENT_TEMPLATES.keys())}


@router.post("/event/budget", summary="Budget recommendation for event type")
async def event_budget(event_type: str = "corporate", guest_count: int = 100):
    from .event_assistant import EVENT_TEMPLATES
    tmpl = EVENT_TEMPLATES.get(event_type, EVENT_TEMPLATES["corporate"])
    return {
        "event_type": event_type,
        "budget_range": tmpl["budget_range"],
        "recommended_budget": tmpl["budget_range"]["typical"],
        "typical_line_items": tmpl["typical_line_items"],
    }


@router.post("/event/vendors", summary="Vendor recommendations")
async def event_vendors(event_type: str = "corporate", guest_count: int = 100):
    from .event_assistant import EventAssistant, EVENT_TEMPLATES
    tmpl = EVENT_TEMPLATES.get(event_type, EVENT_TEMPLATES["corporate"])
    assistant = get_event_assistant()
    return {"vendors": assistant._suggest_vendors(tmpl, guest_count)}


@router.post("/event/staff", summary="Staff recommendations")
async def event_staff(event_type: str = "corporate", guest_count: int = 100):
    from .event_assistant import EventAssistant, EVENT_TEMPLATES
    tmpl = EVENT_TEMPLATES.get(event_type, EVENT_TEMPLATES["corporate"])
    assistant = get_event_assistant()
    return {"staff": assistant._suggest_staff(tmpl, guest_count)}


# ══════════════════════════════════════════════════════════════════════════
# MODULE B: INTELLIGENT PO GENERATOR
# ══════════════════════════════════════════════════════════════════════════

@router.post("/po/generate", response_model=POGenerateResponse,
             summary="Generate POs from event with budget guardrails")
async def po_generate(request: POGenerateRequest):
    assistant = get_po_assistant()
    return assistant.generate(request)


@router.post("/po/optimize", summary="Optimize supplier selection")
async def po_optimize(line_items: list, preferred_only: bool = False):
    assistant = get_po_assistant()
    return {"optimizations": assistant.optimize_supplier(line_items, preferred_only)}


# ══════════════════════════════════════════════════════════════════════════
# MODULE C: SMART RECONCILIATION v2
# ══════════════════════════════════════════════════════════════════════════

@router.post("/recon/batch", response_model=ReconResponse,
             summary="Batch reconcile transactions")
async def recon_batch(request: ReconRequest):
    assistant = get_recon_assistant()
    return assistant.reconcile_batch(request)


@router.post("/recon/single", summary="Single transaction reconcile")
async def recon_single(bank_txn: dict, system_txn: Optional[dict] = None,
                       threshold: float = 0.85):
    assistant = get_recon_assistant()
    return assistant.reconcile_single(bank_txn, system_txn, threshold)


@router.post("/recon/learn", summary="Learn from manual correction")
async def recon_learn(bank_txn: dict, system_txn: dict, correction: Optional[str] = None):
    assistant = get_recon_assistant()
    assistant.learn_from_match(bank_txn, system_txn, correction)
    engine = get_engine()
    return {"status": "learned", "total_patterns": engine.pattern_count()}


@router.get("/recon/patterns", summary="View learned reconciliation patterns")
async def recon_patterns():
    assistant = get_recon_assistant()
    return {"patterns": assistant.get_learned_patterns(), "count": len(assistant.get_learned_patterns())}


# ══════════════════════════════════════════════════════════════════════════
# MODULE D: LIVE FINANCIAL COCKPIT
# ══════════════════════════════════════════════════════════════════════════

@router.get("/financial/events", summary="Event P&L")
async def financial_events(event_id: Optional[int] = None, event_name: Optional[str] = None):
    cockpit = get_financial_cockpit()
    return cockpit.get_event_pnl(event_id, event_name)


@router.get("/financial/cashflow", summary="Cash flow projection")
async def financial_cashflow(weeks: int = 8):
    cockpit = get_financial_cockpit()
    return cockpit.get_cashflow_projection(weeks)


@router.get("/financial/summary", response_model=FinancialSummary,
            summary="Company financial summary")
async def financial_summary(period: str = "current_month"):
    cockpit = get_financial_cockpit()
    return cockpit.get_summary(period)


# ══════════════════════════════════════════════════════════════════════════
# CO-PILOT UI PANEL
# ══════════════════════════════════════════════════════════════════════════

@router.post("/panel", response_model=PanelResponse,
             summary="Contextual co-pilot panel for any form")
async def copilot_panel(request: PanelRequest):
    engine = get_engine()
    suggestions = []
    quick_actions = []
    context_title = ""
    summary = ""

    if request.form_type == "event":
        context_title = "Event Assistant"
        assistant = get_event_assistant()
        analysis = assistant.analyze(EventAnalysisRequest(
            event_name=request.form_data.get("event_name", "") if request.form_data else None,
            budget=request.form_data.get("budget") if request.form_data else None,
        ))
        suggestions = analysis.suggestions
        quick_actions = [
            {"label": "Suggest Budget", "action": "suggest_budget"},
            {"label": "Suggest Vendors", "action": "suggest_vendors"},
        ]
        summary = f"Detected: {analysis.event_type} | Est. budget: ${analysis.estimated_budget:,.0f}"

    elif request.form_type == "po":
        context_title = "PO Assistant"
        assistant = get_po_assistant()
        po_result = assistant.generate(POGenerateRequest(
            event_name=request.form_data.get("event_name", "") if request.form_data else None,
            budget_remaining=request.form_data.get("budget_remaining") if request.form_data else None,
        ))
        suggestions = po_result.suggestions
        budget_s = po_result.budget_status
        quick_actions = [
            {"label": "Auto-Generate", "action": "auto_generate"},
            {"label": "Check Duplicates", "action": "check_duplicates"},
            {"label": "Optimize Supplier", "action": "optimize_supplier"},
        ]
        summary = f"Budget: {budget_s} | Score: {po_result.supplier_score or 'N/A'}"

    elif request.form_type == "recon":
        context_title = "Reconciliation Assistant"
        quick_actions = [
            {"label": "Auto-Match", "action": "auto_match"},
            {"label": "View Patterns", "action": "view_patterns"},
        ]
        summary = f"Patterns learned: {engine.pattern_count()}"

    elif request.form_type == "financial":
        context_title = "Financial Cockpit"
        cockpit = get_financial_cockpit()
        fin = cockpit.get_summary()
        suggestions = [
            Suggestion(id="fin_revenue", type="info",
                       title=f"Revenue: ${fin.revenue:,.0f}",
                       description=f"Margin: {fin.margin_pct}%"),
        ]
        quick_actions = [
            {"label": "View P&L", "action": "view_pnl"},
            {"label": "Cash Flow", "action": "view_cashflow"},
        ]
        summary = f"P&L: ${fin.gross_profit:,.0f} profit | Cash: ${fin.cash_position:,.0f}"

    else:
        context_title = "Co-Pilot Dashboard"
        notif = get_notifications()
        alerts = notif.get_dashboard_notifications("admin")
        if alerts:
            suggestions = [Suggestion(id=a["id"], type=a["severity"],
                           title=a["title"], description=a["message"])
                          for a in alerts[:3]]
        quick_actions = [
            {"label": "Run Analysis", "action": "run_analysis"},
            {"label": "View Notifications", "action": "view_notifications"},
        ]
        summary = f"System ready | {engine.pattern_count()} patterns learned"

    return PanelResponse(
        form_type=request.form_type,
        context_title=context_title,
        suggestions=suggestions,
        quick_actions=quick_actions,
        summary=summary,
        engine_status="ready",
    )


@router.post("/ask", response_model=CoPilotAskResponse,
             summary="Ask the Co-Pilot AI a question")
async def copilot_ask(request: CoPilotAskRequest):
    engine = get_engine()
    llm_answer = engine.ask_llm(request.question)

    if llm_answer:
        answer = llm_answer
        confidence = ConfidenceLevel(score=0.85, label="high", source="local-llm")
    else:
        answer = _rule_based_answer(request.question, request.context or {})
        confidence = ConfidenceLevel(score=0.65, label="medium", source="rule-based")

    return CoPilotAskResponse(
        answer=answer,
        confidence=confidence,
        sources=["local-llm" if llm_answer else "rule-engine"],
        follow_up_questions=[
            "What is the current budget status?",
            "Show me pending POs",
            "Any reconciliation exceptions?",
        ],
    )


def _rule_based_answer(question: str, context: dict) -> str:
    q = question.lower()
    if "health" in q or "status" in q:
        engine = get_engine()
        h = engine.health()
        return (f"System status: {h['status']}. "
                f"Patterns learned: {h['patterns_learned']}. "
                f"AI source: {h['best_source']}.")
    if "budget" in q:
        return "Current budget usage is 62%. Remaining: $1,216,000."
    if "po" in q or "purchase" in q:
        return "There are 3 pending POs for next week's event."
    if "recon" in q or "reconciliation" in q:
        return f"Reconciliation assistant has learned patterns from corrections."
    if "event" in q:
        return "Latest event: Annual Gala Dinner. Budget at 85%."
    return (
        "I can help with: system health, budget status, POs, "
        "reconciliation, and event details. What would you like to know?"
    )
