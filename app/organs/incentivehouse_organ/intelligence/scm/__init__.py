"""
intelligence/scm/__init__.py
Strategic Cost Management analyzers for IHE-ERP.
3 cells: ValueChain, StrategicCost, Sustainability.
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger("incentivehouse_organ.intelligence.scm")


def analyze_value_chain(db: Session) -> dict:
    """Analyze cost flow across primary activities (procure -> ops -> sales)."""
    out = {"cell": "value_chain", "generated_at": datetime.now().isoformat()}
    try:
        # Sum of purchases (inbound), opex (operations), sales revenue (outbound)
        purchases = db.execute(text(
            "SELECT COALESCE(SUM(total_amount), 0) FROM purchase_voucher"
        )).scalar() or 0
        sales = db.execute(text(
            "SELECT COALESCE(SUM(total_amount), 0) FROM sales_invoice"
        )).scalar() or 0
        bank = db.execute(text(
            "SELECT COALESCE(SUM(amount), 0) FROM bank_transaction WHERE amount > 0"
        )).scalar() or 0
        out.update({
            "status": "ok",
            "inbound_logistics": float(purchases),
            "operations": float(bank),
            "outbound_logistics": float(sales),
            "value_added": float(sales - purchases),
            "value_chain_margin_pct": round((sales - purchases) / sales * 100, 2) if sales else 0,
        })
    except Exception as exc:
        out["status"] = "error"
        out["error"] = str(exc)
    return out


def analyze_strategic_cost(db: Session) -> dict:
    """Cost driver analysis: identify highest-cost categories."""
    out = {"cell": "strategic_cost", "generated_at": datetime.now().isoformat()}
    try:
        # Top 5 vendors by spend
        top_vendors = db.execute(text("""
            SELECT vendor_id, COALESCE(SUM(total_amount), 0) as total
            FROM purchase_voucher
            GROUP BY vendor_id
            ORDER BY total DESC
            LIMIT 5
        """)).fetchall()
        out["status"] = "ok"
        out["top_cost_drivers"] = [
            {"vendor_id": r[0], "total_spend": float(r[1])} for r in top_vendors
        ]
        total_spend = sum(float(r[1]) for r in top_vendors)
        out["top_5_concentration_pct"] = round(total_spend / sum(float(r[1]) for r in top_vendors) * 100, 1) if total_spend else 0
    except Exception as exc:
        out["status"] = "error"
        out["error"] = str(exc)
    return out


def analyze_sustainability(db: Session) -> dict:
    """Sustainability scoring based on digital footprint and efficiency."""
    out = {"cell": "sustainability", "generated_at": datetime.now().isoformat()}
    try:
        digital_records = 0
        paper_records = 0
        try:
            digital_records = db.execute(text(
                "SELECT COUNT(*) FROM supporting_document WHERE digital_signature = 1 OR is_digital = 1"
            )).scalar() or 0
            paper_records = db.execute(text(
                "SELECT COUNT(*) FROM supporting_document WHERE (digital_signature IS NULL OR digital_signature = 0) AND (is_digital IS NULL OR is_digital = 0)"
            )).scalar() or 0
        except Exception:
            # If supporting_document table doesn't have those columns, use audit_trail as a proxy
            try:
                digital_records = db.execute(text(
                    "SELECT COUNT(*) FROM audit_trail WHERE action != 'BACKUP'"
                )).scalar() or 0
            except Exception:
                digital_records = 0
        total = digital_records + paper_records
        digital_pct = (digital_records / total * 100) if total else 100
        score = min(100.0, digital_pct + 10)  # +10 baseline for using ERP at all
        out.update({
            "status": "ok",
            "digital_records": int(digital_records),
            "paper_records": int(paper_records),
            "digital_pct": round(digital_pct, 1),
            "sustainability_score": round(score, 1),
            "grade": "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D",
        })
    except Exception as exc:
        out["status"] = "error"
        out["error"] = str(exc)
    return out


def run_scm_analysis(db: Session, cell: str = "all") -> dict:
    """Run one or all SCM cells."""
    result = {"version": "2.3.0", "generated_at": datetime.now().isoformat()}
    if cell in ("value_chain", "all"):
        result["value_chain"] = analyze_value_chain(db)
    if cell in ("strategic_cost", "all"):
        result["strategic_cost"] = analyze_strategic_cost(db)
    if cell in ("sustainability", "all"):
        result["sustainability"] = analyze_sustainability(db)
    return result
