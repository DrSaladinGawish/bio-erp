"""
Co-Pilot Smart Modules for IncentiveHouse ERP.
Local AI engine — fully offline, no cloud APIs.
"""

from .engine import CoPilotEngine
from .schemas import (
    EventAnalysisRequest, EventAnalysisResponse,
    POGenerateRequest, POGenerateResponse,
    ReconRequest, ReconResponse,
    FinancialSummary, FinancialAlert,
    PanelRequest, PanelResponse,
    CoPilotAskRequest, CoPilotAskResponse,
    Pattern, Suggestion, ConfidenceLevel,
)
from .event_assistant import EventAssistant
from .po_assistant import POAssistant
from .recon_assistant import ReconAssistant
from .financial_cockpit import FinancialCockpit
from .notifications import NotificationEngine

__version__ = "1.0.0"
