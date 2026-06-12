"""
NotificationEngine — Contextual Alert System for IncentiveHouse ERP

Sends smart alerts like:
- "Budget 80% used — Event #123"
- "Supplier XYZ delayed 3x this month"
- "Event starts in 2 days — POs not confirmed"
- "Cash balance projected negative in 7 days"

All processing is local. No cloud APIs.
"""

from __future__ import annotations
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .engine import CoPilotEngine, ConfidenceLevel

logger = logging.getLogger("copilot.notifications")


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    SUCCESS = "success"


@dataclass
class Alert:
    """A contextual alert for the user."""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    category: str  # "budget", "supplier", "event", "cashflow", "staff"
    entity_id: Optional[int] = None
    entity_type: Optional[str] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    dismiss_after_days: int = 7
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "action_url": self.action_url,
            "action_label": self.action_label,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_dismissible": True,
        }


class NotificationEngine:
    """
    Contextual Alert Engine — monitors ERP data and generates smart notifications.

    Can be called:
    - On page load (dashboard alerts)
    - On form open (contextual alerts)
    - Via background task (periodic checks)
    - Via webhook (event triggers)
    """

    def __init__(self, engine: CoPilotEngine, db_session_factory=None):
        self.engine = engine
        self.db = db_session_factory
        self._alert_cache: List[Alert] = []
        self._last_check: Optional[datetime] = None

    # ═══════════════════════════════════════════════════════════════
    # Main Entry: Get All Alerts for User
    # ═══════════════════════════════════════════════════════════════

    def get_alerts(
        self,
        user_role: str = "user",
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        max_alerts: int = 20,
    ) -> List[Alert]:
        """
        Get all relevant alerts for the current context.

        Args:
            user_role: Filter by role (admin sees all, finance sees financial, etc.)
            entity_type: Filter by entity type ("event", "po", etc.)
            entity_id: Filter by specific entity
            max_alerts: Maximum alerts to return
        """
        alerts = []

        # Budget alerts
        if user_role in ("admin", "manager", "finance"):
            alerts.extend(self._check_budget_alerts(entity_type, entity_id))

        # Supplier alerts
        if user_role in ("admin", "manager", "ops", "procurement"):
            alerts.extend(self._check_supplier_alerts(entity_type, entity_id))

        # Event alerts
        if user_role in ("admin", "manager", "ops", "sales"):
            alerts.extend(self._check_event_alerts(entity_type, entity_id))

        # Cash flow alerts (finance only)
        if user_role in ("admin", "finance"):
            alerts.extend(self._check_cashflow_alerts())

        # Staff alerts (ops only)
        if user_role in ("admin", "manager", "ops"):
            alerts.extend(self._check_staff_alerts(entity_type, entity_id))

        # Sort by severity then date
        severity_order = {AlertSeverity.CRITICAL: 0, AlertSeverity.WARNING: 1, 
                         AlertSeverity.INFO: 2, AlertSeverity.SUCCESS: 3}
        alerts.sort(key=lambda a: (severity_order.get(a.severity, 99), a.created_at), reverse=False)

        return alerts[:max_alerts]

    # ═══════════════════════════════════════════════════════════════
    # Budget Alerts
    # ═══════════════════════════════════════════════════════════════

    def _check_budget_alerts(
        self,
        entity_type: Optional[str],
        entity_id: Optional[int],
    ) -> List[Alert]:
        """Check for budget-related alerts."""
        alerts = []

        # In production: query events with budget variance > threshold
        # Mock alerts for demonstration

        alerts.append(Alert(
            id="budget-001",
            severity=AlertSeverity.WARNING,
            title="Budget Variance: CISCO Annual Meet",
            message="Event #1 is 7.1% over planned budget (680K vs 700K planned). Review cost allocations.",
            category="budget",
            entity_id=1,
            entity_type="event",
            action_url="/events/1/budget",
            action_label="Review Budget",
        ))

        alerts.append(Alert(
            id="budget-002",
            severity=AlertSeverity.CRITICAL,
            title="Budget Exceeded: Microsoft Launch",
            message="Event #2 exceeded budget by 6.7% (480K vs 450K planned). Executive approval required for overrun.",
            category="budget",
            entity_id=2,
            entity_type="event",
            action_url="/events/2/budget",
            action_label="Approve Overrun",
        ))

        return alerts

    # ═══════════════════════════════════════════════════════════════
    # Supplier Alerts
    # ═══════════════════════════════════════════════════════════════

    def _check_supplier_alerts(
        self,
        entity_type: Optional[str],
        entity_id: Optional[int],
    ) -> List[Alert]:
        """Check for supplier-related alerts."""
        alerts = []

        alerts.append(Alert(
            id="supp-001",
            severity=AlertSeverity.WARNING,
            title="Supplier Delay Pattern: AudioVis Pro",
            message="AudioVis Pro has been delayed in 3 of last 5 events. Consider alternative for upcoming events.",
            category="supplier",
            entity_id=1,
            entity_type="supplier",
            action_url="/suppliers/1",
            action_label="View Supplier",
        ))

        return alerts

    # ═══════════════════════════════════════════════════════════════
    # Event Alerts
    # ═══════════════════════════════════════════════════════════════

    def _check_event_alerts(
        self,
        entity_type: Optional[str],
        entity_id: Optional[int],
    ) -> List[Alert]:
        """Check for event-related alerts."""
        alerts = []

        # Event approaching without confirmed POs
        alerts.append(Alert(
            id="evt-001",
            severity=AlertSeverity.CRITICAL,
            title="Event in 2 Days — POs Not Confirmed",
            message="CISCO Annual Meet starts in 2 days but 3 POs are still pending supplier confirmation.",
            category="event",
            entity_id=1,
            entity_type="event",
            action_url="/events/1/pos",
            action_label="View POs",
        ))

        # Completed event with outstanding invoices
        alerts.append(Alert(
            id="evt-002",
            severity=AlertSeverity.WARNING,
            title="Completed Event — Outstanding Invoices",
            message="Microsoft Product Launch is completed but 150K EGP in invoices remain uncollected.",
            category="event",
            entity_id=2,
            entity_type="event",
            action_url="/events/2/invoices",
            action_label="Send Reminder",
        ))

        return alerts

    # ═══════════════════════════════════════════════════════════════
    # Cash Flow Alerts
    # ═══════════════════════════════════════════════════════════════

    def _check_cashflow_alerts(self) -> List[Alert]:
        """Check for cash flow alerts."""
        alerts = []

        alerts.append(Alert(
            id="cash-001",
            severity=AlertSeverity.CRITICAL,
            title="Negative Cash Projected in 7 Days",
            message="Based on outstanding payables and receivables, cash balance is projected to go negative by June 19, 2026. Accelerate collections or defer non-critical payments.",
            category="cashflow",
            action_url="/finance/cashflow",
            action_label="View Projection",
        ))

        alerts.append(Alert(
            id="cash-002",
            severity=AlertSeverity.INFO,
            title="Collection Opportunity",
            message="2 clients have invoices due this week totaling 450K EGP. Follow up for faster collection.",
            category="cashflow",
            action_url="/finance/invoices",
            action_label="View Invoices",
        ))

        return alerts

    # ═══════════════════════════════════════════════════════════════
    # Staff Alerts
    # ═══════════════════════════════════════════════════════════════

    def _check_staff_alerts(
        self,
        entity_type: Optional[str],
        entity_id: Optional[int],
    ) -> List[Alert]:
        """Check for staff-related alerts."""
        alerts = []

        alerts.append(Alert(
            id="staff-001",
            severity=AlertSeverity.WARNING,
            title="Staff Conflict: June 15-17",
            message="Ahmed (Lead) is assigned to both CISCO Annual Meet and Noventiq Conference on overlapping dates. Reassign one event.",
            category="staff",
            entity_id=1,
            entity_type="event",
            action_url="/staff/schedule",
            action_label="View Schedule",
        ))

        return alerts

    # ═══════════════════════════════════════════════════════════════
    # Background Task: Periodic Check
    # ═══════════════════════════════════════════════════════════════

    def run_periodic_check(self) -> List[Alert]:
        """
        Run all checks and cache results. Call from background task.
        Returns new alerts since last check.
        """
        now = datetime.now()

        # Only run if enough time passed (avoid spam)
        if self._last_check and (now - self._last_check) < timedelta(minutes=5):
            return []

        all_alerts = self.get_alerts(user_role="admin", max_alerts=50)

        # Find new alerts (not in cache)
        cached_ids = {a.id for a in self._alert_cache}
        new_alerts = [a for a in all_alerts if a.id not in cached_ids]

        self._alert_cache = all_alerts
        self._last_check = now

        if new_alerts:
            logger.info(f"Generated {len(new_alerts)} new alerts")

        return new_alerts

    # ═══════════════════════════════════════════════════════════════
    # Alert Management
    # ═══════════════════════════════════════════════════════════════

    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an alert by ID."""
        self._alert_cache = [a for a in self._alert_cache if a.id != alert_id]
        return True

    def get_alert_count(self, user_role: str = "user") -> Dict[str, int]:
        """Get alert counts by severity."""
        alerts = self.get_alerts(user_role=user_role)
        counts = {"critical": 0, "warning": 0, "info": 0, "success": 0, "total": len(alerts)}
        for a in alerts:
            counts[a.severity.value] += 1
        return counts
