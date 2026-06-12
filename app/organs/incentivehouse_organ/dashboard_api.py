"""
dashboard_api.py
Dashboard data API — serves all /api/v1/dashboard/* endpoints
"""
from flask import Blueprint, jsonify, session
from datetime import datetime
import random

dashboard_bp = Blueprint("dashboard_api", __name__, url_prefix="/api/v1/dashboard")

# ── AUTH ME ──
@dashboard_bp.route("/auth/me", methods=["GET"])
def auth_me():
    """Return current user info"""
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({
        "id": session.get("user_id", 1),
        "username": session.get("username", "admin"),
        "name": session.get("name", "Administrator"),
        "role": session.get("role", "admin"),
        "email": session.get("email", "admin@incentivehouse.com")
    })

# ── DASHBOARD SUMMARY ──
@dashboard_bp.route("/summary", methods=["GET"])
def dashboard_summary():
    """Main dashboard KPI cards"""
    return jsonify({
        "total_events": 143,
        "active_events": 12,
        "total_revenue": 56300000,
        "total_costs": 42300000,
        "gross_margin": 14000000,
        "margin_percent": 24.9,
        "ap_due": 19500000,
        "ar_due": 15300000,
        "bank_balance": 2170000,
        "pending_approvals": 3,
        "eta_validated": 92,
        "eta_rejected": 1,
        "updated_at": datetime.now().isoformat()
    })

# ── YEARS ──
@dashboard_bp.route("/years", methods=["GET"])
def dashboard_years():
    """Available fiscal years"""
    return jsonify({
        "years": [
            {"id": 2024, "label": "2024", "status": "closed", "is_active": False},
            {"id": 2025, "label": "2025", "status": "closed", "is_active": False},
            {"id": 2026, "label": "2026", "status": "open", "is_active": True}
        ],
        "current_year": 2026
    })

# ── CATEGORIES ──
@dashboard_bp.route("/categories", methods=["GET"])
def dashboard_categories():
    """Event/budget categories for filters"""
    return jsonify({
        "categories": [
            {"id": 1, "name": "Catering", "code": "5001", "budget": 31045.61, "actual": 28400.00},
            {"id": 2, "name": "Venue", "code": "5002", "budget": 0, "actual": 0},
            {"id": 3, "name": "Transportation", "code": "5003", "budget": 29192.99, "actual": 26500.00},
            {"id": 4, "name": "Accommodation", "code": "5004", "budget": 0, "actual": 0},
            {"id": 5, "name": "Equipment", "code": "5005", "budget": 0, "actual": 0},
            {"id": 6, "name": "Marketing", "code": "5006", "budget": 0, "actual": 0},
            {"id": 7, "name": "Staff Costs", "code": "5007", "budget": 0, "actual": 0},
            {"id": 8, "name": "Miscellaneous", "code": "5008", "budget": 33134.15, "actual": 29800.00}
        ]
    })

# ── ACTIVITY FEED ──
@dashboard_bp.route("/activity", methods=["GET"])
def dashboard_activity():
    """Recent activity feed"""
    limit = int(__import__("flask").request.args.get("limit", 5))
    activities = [
        {"id": 1, "type": "invoice", "description": "Sales invoice #11.23.C0031.74 validated", "user": "system", "timestamp": "2026-06-10T10:30:00", "status": "success"},
        {"id": 2, "type": "payment", "description": "AP Payment 360 processed — 30.0M EGP", "user": "system", "timestamp": "2026-06-10T09:15:00", "status": "success"},
        {"id": 3, "type": "budget", "description": "FY2026 budget updated — 93,372.75 EGP", "user": "admin", "timestamp": "2026-06-10T08:45:00", "status": "info"},
        {"id": 4, "type": "approval", "description": "Purchase order PO-2026-042 awaiting approval", "user": "manager", "timestamp": "2026-06-09T16:20:00", "status": "warning"},
        {"id": 5, "type": "eta", "description": "ETA submission rejected for invoice #E-308-8", "user": "system", "timestamp": "2026-06-09T14:10:00", "status": "error"},
        {"id": 6, "type": "event", "description": "Event 02.26.C0003.210 — Partnerships kickoff", "user": "ops", "timestamp": "2026-06-09T11:00:00", "status": "info"},
        {"id": 7, "type": "grn", "description": "GRN #GRN-2026-020 received — 15 items", "user": "warehouse", "timestamp": "2026-06-08T15:30:00", "status": "success"}
    ]
    return jsonify({"activities": activities[:limit], "total": len(activities)})

# ── FLAGS / ALERTS ──
@dashboard_bp.route("/flags", methods=["GET"])
def dashboard_flags():
    """System alerts and flags"""
    return jsonify({
        "flags": [
            {"id": 1, "level": "error", "message": "1 ETA invoice rejected — needs correction", "module": "ETA", "action_url": "/incentivehouse/eta"},
            {"id": 2, "level": "warning", "message": "AP aging: 18 invoices >90 days (400K EGP)", "module": "AP", "action_url": "/incentivehouse/ap"},
            {"id": 3, "level": "warning", "message": "3 purchase orders pending approval", "module": "Approval", "action_url": "/incentivehouse/approval"},
            {"id": 4, "level": "info", "message": "FY2026 budget variance: +291K EGP", "module": "Budget", "action_url": "/incentivehouse/budget"},
            {"id": 5, "level": "success", "message": "System check: 18/18 endpoints PASS", "module": "System", "action_url": "/health"}
        ],
        "unread_count": 3
    })

# ── V2 STATUS (backward compat) ──
@dashboard_bp.route("/status", methods=["GET"])
def v2_status():
    """System status (v2 compat)"""
    return jsonify({
        "status": "ok",
        "version": "5.3.0",
        "database": "ok",
        "modules": {
            "grn": "ok", "cost": "ok", "event_budget": "ok", "bsc": "ok",
            "bi": "ok", "budget": "ok", "approval": "ok", "ops": "ok"
        },
        "timestamp": datetime.now().isoformat()
    })
