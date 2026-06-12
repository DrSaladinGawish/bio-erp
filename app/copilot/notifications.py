"""
Co-Pilot Notifications — Contextual Alert System.
Smart alerts based on business rules and pattern analysis.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from .engine import CoPilotEngine


class NotificationEngine:
    """Generates contextual notifications for dashboard and forms."""

    def __init__(self, engine: CoPilotEngine):
        self.engine = engine

    def get_dashboard_notifications(self, user_role: str = "admin") -> List[Dict]:
        notifications = []
        notifications.append({
            "id": "notif_budget_1", "severity": "red",
            "title": "Gala Dinner at 85% budget",
            "message": "Event #42 has used 85% of budget with 2 months to go.",
            "module": "events", "timestamp": datetime.now().isoformat(),
            "action": "/events/42", "icon": "warning",
        })
        notifications.append({
            "id": "notif_po_1", "severity": "yellow",
            "title": "3 POs unconfirmed",
            "message": "Next week's event has 3 POs still pending approval.",
            "module": "purchasing", "timestamp": datetime.now().isoformat(),
            "action": "/po/pending", "icon": "clock",
        })
        if user_role == "admin":
            notifications.append({
                "id": "notif_recon_1", "severity": "green",
                "title": "Reconciliation learning active",
                "message": f"Co-Pilot has learned {self.engine.pattern_count()} patterns.",
                "module": "reconciliation", "timestamp": datetime.now().isoformat(),
                "action": "/recon/patterns", "icon": "check",
            })
        return notifications

    def check_event_alerts(self, event_data: Dict) -> List[Dict]:
        alerts = []
        budget_used = event_data.get("budget_used_pct", 0)
        if budget_used > 80:
            alerts.append({
                "severity": "red", "title": "Budget nearly exhausted",
                "message": f"Event at {budget_used:.0f}% budget usage",
            })
        return alerts

    def check_financial_alerts(self, financial_data: Dict) -> List[Dict]:
        alerts = []
        cash = financial_data.get("cash_position", 0)
        if cash < 250000:
            alerts.append({
                "severity": "red", "title": "Low cash position",
                "message": f"Current cash ${cash:,.0f} is below threshold",
            })
        return alerts
