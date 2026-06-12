"""
Smart Event Builder — Co-Pilot Module A.
Analyzes event requirements, suggests budget, vendors, staff, and templates.
"""

import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from .engine import CoPilotEngine
from .schemas import (
    EventAnalysisRequest, EventAnalysisResponse,
    Suggestion, ConfidenceLevel,
)

EVENT_TEMPLATES = {
    "corporate": {
        "name": "Corporate Event",
        "budget_range": {"min": 50000, "max": 500000, "typical": 180000},
        "typical_line_items": [
            {"name": "Venue", "pct": 30},
            {"name": "Catering", "pct": 25},
            {"name": "AV & Production", "pct": 15},
            {"name": "Decor & Design", "pct": 10},
            {"name": "Entertainment", "pct": 8},
            {"name": "Marketing", "pct": 7},
            {"name": "Miscellaneous", "pct": 5},
        ],
        "suggested_vendor_types": ["catering", "av", "decor", "entertainment"],
        "suggested_staff_roles": ["event_coordinator", "tech_support", "event_staff"],
    },
    "wedding": {
        "name": "Wedding",
        "budget_range": {"min": 80000, "max": 500000, "typical": 250000},
        "typical_line_items": [
            {"name": "Venue", "pct": 35},
            {"name": "Catering", "pct": 25},
            {"name": "Photography", "pct": 10},
            {"name": "Decor", "pct": 12},
            {"name": "Attire", "pct": 8},
            {"name": "Entertainment", "pct": 5},
            {"name": "Miscellaneous", "pct": 5},
        ],
        "suggested_vendor_types": ["catering", "photography", "decor", "entertainment"],
        "suggested_staff_roles": ["wedding_planner", "event_staff"],
    },
    "conference": {
        "name": "Conference",
        "budget_range": {"min": 100000, "max": 1000000, "typical": 350000},
        "typical_line_items": [
            {"name": "Venue", "pct": 25},
            {"name": "Catering", "pct": 20},
            {"name": "AV & Production", "pct": 20},
            {"name": "Speaker Fees", "pct": 15},
            {"name": "Marketing", "pct": 10},
            {"name": "Logistics", "pct": 10},
        ],
        "suggested_vendor_types": ["av", "catering", "logistics", "printing"],
        "suggested_staff_roles": ["event_coordinator", "tech_support", "registration_staff"],
    },
    "private_party": {
        "name": "Private Party",
        "budget_range": {"min": 10000, "max": 100000, "typical": 35000},
        "typical_line_items": [
            {"name": "Venue", "pct": 35},
            {"name": "Catering", "pct": 30},
            {"name": "Decor", "pct": 15},
            {"name": "Entertainment", "pct": 10},
            {"name": "Miscellaneous", "pct": 10},
        ],
        "suggested_vendor_types": ["catering", "decor", "entertainment"],
        "suggested_staff_roles": ["event_staff"],
    },
    "fundraiser": {
        "name": "Fundraiser / Gala",
        "budget_range": {"min": 50000, "max": 300000, "typical": 150000},
        "typical_line_items": [
            {"name": "Venue", "pct": 25},
            {"name": "Catering", "pct": 25},
            {"name": "Entertainment", "pct": 15},
            {"name": "AV & Production", "pct": 10},
            {"name": "Marketing", "pct": 10},
            {"name": "Decor", "pct": 8},
            {"name": "Miscellaneous", "pct": 7},
        ],
        "suggested_vendor_types": ["catering", "av", "entertainment", "printing"],
        "suggested_staff_roles": ["event_coordinator", "event_staff", "volunteer_coordinator"],
    },
}

VENDOR_DB = [
    {"name": "Elite Catering Co.", "type": "catering", "score": 98, "avg_cost_per_guest": 450},
    {"name": "AV Pro Solutions", "type": "av", "score": 92, "avg_cost_per_event": 15000},
    {"name": "Grand Decor Studio", "type": "decor", "score": 88, "avg_cost_per_event": 20000},
    {"name": "Starlight Entertainment", "type": "entertainment", "score": 85, "avg_cost_per_event": 12000},
    {"name": "Capture Photography", "type": "photography", "score": 90, "avg_cost_per_event": 8000},
    {"name": "PrintMaster Marketing", "type": "printing", "score": 82, "avg_cost_per_event": 5000},
    {"name": "LogiPro Logistics", "type": "logistics", "score": 78, "avg_cost_per_event": 7000},
    {"name": "EventStaff Inc.", "type": "staffing", "score": 87, "avg_cost_per_staff": 2500},
    {"name": "SoundWave Audio", "type": "av", "score": 84, "avg_cost_per_event": 10000},
    {"name": "Bloom Floral Design", "type": "decor", "score": 91, "avg_cost_per_event": 12000},
]

STAFF_DB = [
    {"role": "event_coordinator", "name": "Event Coordinator", "count_per_100_guests": 1, "cost_per_event": 5000},
    {"role": "event_staff", "name": "Event Staff", "count_per_100_guests": 4, "cost_per_person": 2000},
    {"role": "tech_support", "name": "AV Tech Support", "count_per_event": 2, "cost_per_person": 3000},
    {"role": "wedding_planner", "name": "Wedding Planner", "count_per_event": 1, "cost_per_event": 8000},
    {"role": "registration_staff", "name": "Registration Staff", "count_per_100_guests": 2, "cost_per_person": 1500},
    {"role": "volunteer_coordinator", "name": "Volunteer Coordinator", "count_per_event": 1, "cost_per_event": 3000},
]


class EventAssistant:
    """
    AI-guided event creation.
    Analyzes requirements, matches templates, suggests budget/vendors/staff.
    """

    def __init__(self, engine: CoPilotEngine):
        self.engine = engine

    def analyze(self, request: EventAnalysisRequest) -> EventAnalysisResponse:
        event_type = request.event_type or self._detect_event_type(request)
        template = EVENT_TEMPLATES.get(event_type, EVENT_TEMPLATES["corporate"])
        budget = request.budget or template["budget_range"]["typical"]

        suggestions = self._build_suggestions(request, template, budget)
        vendors = self._suggest_vendors(template, request.guest_count)
        staff = self._suggest_staff(template, request.guest_count)
        risks = self._assess_risks(request, template, budget)

        budget_rec = template["budget_range"]
        confidence = self.engine.confidence(0.85 if event_type == (request.event_type or event_type) else 0.70)

        return EventAnalysisResponse(
            event_name=request.event_name or "Untitled Event",
            event_type=event_type,
            estimated_budget=budget,
            budget_range={"min": budget_rec["min"], "max": budget_rec["max"], "recommended": budget_rec["typical"]},
            suggested_vendors=vendors,
            suggested_staff=staff,
            suggestions=suggestions,
            risks=risks,
            confidence=confidence,
        )

    def _detect_event_type(self, request: EventAnalysisRequest) -> str:
        text = f"{request.event_name or ''} {request.client_name or ''} {request.venue or ''}"
        best_type = "corporate"
        best_score = 0.0
        for etype, tmpl in EVENT_TEMPLATES.items():
            score = self.engine.similarity(text, tmpl["name"])
            if score > best_score:
                best_score = score
                best_type = etype
        return best_type

    def _build_suggestions(self, request: EventAnalysisRequest, template: dict, budget: float) -> List[Suggestion]:
        suggestions = []
        if request.budget and request.budget > template["budget_range"]["max"]:
            suggestions.append(Suggestion(
                id="budget_above_range", type="warning",
                title="Budget above typical range",
                description=f"Your budget (${request.budget:,.0f}) exceeds typical max of ${template['budget_range']['max']:,.0f}",
                confidence=self.engine.confidence(0.90),
            ))
        elif request.budget and request.budget < template["budget_range"]["min"]:
            suggestions.append(Suggestion(
                id="budget_below_range", type="warning",
                title="Budget below typical range",
                description=f"Your budget (${request.budget:,.0f}) is below typical min of ${template['budget_range']['min']:,.0f}",
                confidence=self.engine.confidence(0.90),
            ))
        if request.line_items:
            for item in request.line_items:
                category = item.get("category", "").lower()
                pct = (item.get("estimated_cost", 0) / budget * 100) if budget > 0 else 0
                for ti in template["typical_line_items"]:
                    if category in ti["name"].lower() or category in ti["name"].lower():
                        if pct > ti["pct"] * 1.5:
                            suggestions.append(Suggestion(
                                id=f"line_item_high_{item.get('name','')}",
                                type="warning",
                                title=f"{item.get('name','')} is {pct:.0f}% of budget",
                                description=f"Typical is {ti['pct']}%. Consider adjusting.",
                                confidence=self.engine.confidence(0.85),
                            ))
        return suggestions

    def _suggest_vendors(self, template: dict, guest_count: Optional[int]) -> List[Dict]:
        return [
            {"name": v["name"], "type": v["type"], "score": v["score"],
             "estimated_cost": v.get("avg_cost_per_guest", 0) * (guest_count or 100) if v["type"] == "catering" else v.get("avg_cost_per_event", 0)}
            for v in VENDOR_DB
            if v["type"] in template.get("suggested_vendor_types", [])
        ][:5]

    def _suggest_staff(self, template: dict, guest_count: Optional[int]) -> List[Dict]:
        guests = guest_count or 100
        staff = []
        for role_name in template.get("suggested_staff_roles", []):
            s = next((x for x in STAFF_DB if x["role"] == role_name), None)
            if s:
                if "count_per_100_guests" in s:
                    count = max(1, round(guests / 100 * s["count_per_100_guests"]))
                else:
                    count = s.get("count_per_event", 1)
                total_cost = s.get("cost_per_event", 0) if "cost_per_event" in s else count * s.get("cost_per_person", 0)
                staff.append({"role": s["name"], "count": count, "estimated_cost": total_cost})
        return staff

    def _assess_risks(self, request: EventAnalysisRequest, template: dict, budget: float) -> List[str]:
        risks = []
        if not request.event_name:
            risks.append("Event name not set")
        if not request.client_name and request.event_type != "private_party":
            risks.append("No client assigned")
        if request.start_date and request.end_date:
            try:
                start = datetime.fromisoformat(request.start_date)
                end = datetime.fromisoformat(request.end_date)
                if (end - start).days < 1:
                    risks.append("Event duration seems very short")
            except:
                pass
        if request.guest_count and request.guest_count < 10:
            risks.append("Low guest count — verify event scale")
        return risks
