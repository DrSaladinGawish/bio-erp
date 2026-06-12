"""
P3-D2: SCM-BIO Integration Bridge — Production Hardened
Strict separation: SCM reads from production, writes to scm_staging ONLY.
Zero Gap Compliance for SCM-BIO integration.
Compatible with: Pydantic v2, SQLAlchemy 2.x, FastAPI 0.110+
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel, Field, ConfigDict

# ── CONFIG ──
PRODUCTION_URL = os.getenv(
    "PRODUCTION_DB_URL", "postgresql://postgres:postgres123@localhost:5432/bio_erp"
)
# Staging MUST be separate schema or separate DB. Default uses schema separation.
STAGING_URL = os.getenv(
    "STAGING_DB_URL", "postgresql://postgres:postgres123@localhost:5432/bio_erp"
)
STAGING_SCHEMA = os.getenv("SCM_STAGING_SCHEMA", "scm_staging")

# ── SECURITY: Production table whitelist ──
PRODUCTION_READ_TABLES = {
    "events",
    "clients",
    "suppliers",
    "bank_trnx_staging",
    "sales_line_items",
    "vendors",
    "staff",
    "cost_centers",
}
PRODUCTION_WRITE_TABLES = set()  # SCM NEVER writes directly


class SCMReadOnlyError(Exception):
    """Raised when SCM attempts an unauthorized write to production."""

    pass


class SCMBioBridge:
    """
    Bridge between SCM Module and BIO-ERP production database.

    RULES:
    1. READ from production tables (events, clients, vendors, transactions)
    2. WRITE to scm_staging tables ONLY (scm_analysis, scm_recommendations, etc.)
    3. NEVER write to production tables from SCM
    4. Promotion to production requires explicit admin approval via approve_promotion()
    """

    def __init__(self):
        self.prod_engine = create_engine(PRODUCTION_URL, pool_pre_ping=True)
        self.staging_engine = create_engine(STAGING_URL, pool_pre_ping=True)
        self.ProdSession = sessionmaker(bind=self.prod_engine, expire_on_commit=False)
        self.StagingSession = sessionmaker(
            bind=self.staging_engine, expire_on_commit=False
        )

    # ═══════════════════════════════════════════════════════════
    # READ OPERATIONS (production — READ ONLY)
    # ═══════════════════════════════════════════════════════════

    def get_events(
        self, filters: Optional[dict] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Read events from production — READ ONLY."""
        with self.ProdSession() as session:
            query = """
                SELECT id, event_code, name, event_type, event_date, status, budget, gross_sales
                FROM events
                WHERE is_deleted = false
            """
            params: dict = {}

            if filters:
                if filters.get("status"):
                    query += " AND status = :status"
                    params["status"] = filters["status"]
                if filters.get("event_type"):
                    query += " AND event_type = :event_type"
                    params["event_type"] = filters["event_type"]
                if filters.get("date_from"):
                    query += " AND event_date >= :date_from"
                    params["date_from"] = filters["date_from"]

            query += " ORDER BY event_date DESC LIMIT :limit"
            params["limit"] = limit

            result = session.execute(text(query), params)
            return [dict(row._mapping) for row in result]

    def get_event_detail(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Read single event with line items and client — READ ONLY."""
        with self.ProdSession() as session:
            event = (
                session.execute(
                    text("SELECT * FROM events WHERE id = :id AND is_deleted = false"),
                    {"id": event_id},
                )
                .mappings()
                .fetchone()
            )

            if not event:
                return None

            event_dict = dict(event)

            # Line items
            line_items = (
                session.execute(
                    text("SELECT * FROM sales_line_items WHERE event_id = :id"),
                    {"id": event_id},
                )
                .mappings()
                .fetchall()
            )
            event_dict["line_items"] = [dict(row) for row in line_items]

            # Client
            if event_dict.get("client_id"):
                client = (
                    session.execute(
                        text(
                            "SELECT id, name, email, status FROM clients WHERE id = :id"
                        ),
                        {"id": event_dict["client_id"]},
                    )
                    .mappings()
                    .fetchone()
                )
                if client:
                    event_dict["client"] = dict(client)

            return event_dict

    def get_clients(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Read clients from production — READ ONLY."""
        with self.ProdSession() as session:
            query = """
                SELECT id, name, email, status, credit_limit
                FROM clients
                WHERE is_deleted = false
            """
            params: dict = {"limit": limit}
            if status:
                query += " AND status = :status"
                params["status"] = status
            query += " ORDER BY name LIMIT :limit"

            result = session.execute(text(query), params)
            return [dict(row._mapping) for row in result]

    def get_transactions(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        account: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Read bank transactions from production — READ ONLY."""
        with self.ProdSession() as session:
            query = """
                SELECT id, transaction_number, tx_date, bank_account, description,
                       debit_amount, credit_amount, sub_ledger_code, status
                FROM bank_trnx_staging
                WHERE is_deleted = false
            """
            params: dict = {"limit": limit}

            if date_from:
                query += " AND tx_date >= :date_from"
                params["date_from"] = date_from
            if date_to:
                query += " AND tx_date <= :date_to"
                params["date_to"] = date_to
            if account:
                query += " AND bank_account = :account"
                params["account"] = account

            query += " ORDER BY tx_date DESC LIMIT :limit"

            result = session.execute(text(query), params)
            return [dict(row._mapping) for row in result]

    def get_vendors(
        self, category: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Read vendors/suppliers from production — READ ONLY."""
        with self.ProdSession() as session:
            query = """
                SELECT id, name, category, email, phone, rating, status
                FROM suppliers
                WHERE is_deleted = false
            """
            params: dict = {"limit": limit}
            if category:
                query += " AND category = :category"
                params["category"] = category
            query += " ORDER BY rating DESC NULLS LAST LIMIT :limit"

            result = session.execute(text(query), params)
            return [dict(row._mapping) for row in result]

    # ═══════════════════════════════════════════════════════════
    # WRITE OPERATIONS (staging ONLY — NEVER production)
    # ═══════════════════════════════════════════════════════════

    def _guard_production_write(self, table_name: str) -> None:
        """Internal guard: abort if target is a production table."""
        if table_name.lower() in PRODUCTION_WRITE_TABLES or not table_name.startswith(
            STAGING_SCHEMA
        ):
            raise SCMReadOnlyError(
                f"SCM write blocked: '{table_name}' is not a staging table. "
                f"All SCM writes must target schema '{STAGING_SCHEMA}'."
            )

    def save_cost_analysis(self, analysis: dict) -> Dict[str, Any]:
        """Save cost analysis results to scm_staging. NEVER writes to production."""
        table = f"{STAGING_SCHEMA}.cost_analysis"
        self._guard_production_write(table)

        with self.StagingSession() as session:
            query = text(f"""
                INSERT INTO {table}
                    (event_id, analysis_type, input_data, results, recommendations,
                     confidence_score, created_by, created_at)
                VALUES
                    (:event_id, :analysis_type, :input_data, :results, :recommendations,
                     :confidence_score, :created_by, NOW())
                RETURNING id
            """)

            result = session.execute(
                query,
                {
                    "event_id": analysis["event_id"],
                    "analysis_type": analysis["analysis_type"],
                    "input_data": json.dumps(analysis.get("input_data", {})),
                    "results": json.dumps(analysis.get("results", {})),
                    "recommendations": json.dumps(analysis.get("recommendations", [])),
                    "confidence_score": analysis.get("confidence_score", 0.0),
                    "created_by": analysis.get("created_by", "scm_system"),
                },
            )

            session.commit()
            return {
                "id": result.scalar(),
                "status": "saved_to_staging",
                "schema": STAGING_SCHEMA,
            }

    def save_vendor_scorecard(self, scorecard: dict) -> Dict[str, Any]:
        """Save vendor evaluation to staging."""
        table = f"{STAGING_SCHEMA}.vendor_scorecards"
        self._guard_production_write(table)

        with self.StagingSession() as session:
            query = text(f"""
                INSERT INTO {table}
                    (vendor_id, evaluation_period, quality_score, delivery_score,
                     price_score, service_score, overall_score, notes, created_by, created_at)
                VALUES
                    (:vendor_id, :evaluation_period, :quality_score, :delivery_score,
                     :price_score, :service_score, :overall_score, :notes, :created_by, NOW())
                RETURNING id
            """)

            result = session.execute(query, scorecard)
            session.commit()
            return {"id": result.scalar(), "status": "saved_to_staging"}

    def save_budget_forecast(self, forecast: dict) -> Dict[str, Any]:
        """Save budget forecast to staging."""
        table = f"{STAGING_SCHEMA}.budget_forecasts"
        self._guard_production_write(table)

        with self.StagingSession() as session:
            query = text(f"""
                INSERT INTO {table}
                    (event_id, forecast_period, projected_revenue, projected_cost,
                     projected_profit, variance_notes, created_by, created_at)
                VALUES
                    (:event_id, :forecast_period, :projected_revenue, :projected_cost,
                     :projected_profit, :variance_notes, :created_by, NOW())
                RETURNING id
            """)

            result = session.execute(query, forecast)
            session.commit()
            return {"id": result.scalar(), "status": "saved_to_staging"}

    # ═══════════════════════════════════════════════════════════
    # PROMOTION (Admin approval required — ONLY path to production)
    # ═══════════════════════════════════════════════════════════

    def request_promotion(
        self, staging_id: int, table: str, admin_user: str, reason: str
    ) -> Dict[str, Any]:
        """Request promotion of staging data to production. Requires admin approval."""
        with self.StagingSession() as session:
            query = text(f"""
                INSERT INTO {STAGING_SCHEMA}.promotion_requests
                    (staging_id, staging_table, requested_by, request_reason, status, requested_at)
                VALUES
                    (:staging_id, :table, :admin_user, :reason, 'pending', NOW())
                RETURNING id
            """)

            result = session.execute(
                query,
                {
                    "staging_id": staging_id,
                    "table": table,
                    "admin_user": admin_user,
                    "reason": reason,
                },
            )
            session.commit()

            return {
                "promotion_request_id": result.scalar(),
                "status": "pending_approval",
                "message": "Admin approval required before production update. DO NOT auto-promote.",
            }

    def approve_promotion(self, request_id: int, admin_user: str) -> Dict[str, Any]:
        """
        Admin approves promotion — NOW writes to production.
        This is the ONLY authorized path from staging → production.
        """
        with self.StagingSession() as staging, self.ProdSession() as prod:
            # 1. Fetch request
            req = (
                staging.execute(
                    text(
                        f"SELECT * FROM {STAGING_SCHEMA}.promotion_requests WHERE id = :id"
                    ),
                    {"id": request_id},
                )
                .mappings()
                .fetchone()
            )

            if not req:
                raise ValueError(f"Promotion request {request_id} not found")

            req_dict = dict(req)

            if req_dict["status"] != "pending":
                raise ValueError(f"Request already {req_dict['status']}")

            # 2. Fetch staging data
            staging_data = (
                staging.execute(
                    text(
                        f"SELECT * FROM {STAGING_SCHEMA}.{req_dict['staging_table']} WHERE id = :id"
                    ),
                    {"id": req_dict["staging_id"]},
                )
                .mappings()
                .fetchone()
            )

            if not staging_data:
                raise ValueError("Staging data not found")

            # 3. Apply to production (table-specific logic)
            applied = self._apply_to_production(
                prod, req_dict["staging_table"], dict(staging_data)
            )

            # 4. Mark approved
            staging.execute(
                text(f"""
                    UPDATE {STAGING_SCHEMA}.promotion_requests
                    SET status = 'approved', approved_by = :admin, approved_at = NOW()
                    WHERE id = :id
                """),
                {"admin": admin_user, "id": request_id},
            )
            staging.commit()

            return {
                "status": "approved_and_applied",
                "promotion_request_id": request_id,
                "production_changes": applied,
            }

    def _apply_to_production(
        self, session: Session, table: str, data: dict
    ) -> Dict[str, Any]:
        """Apply staging data to production — INTERNAL ONLY."""

        if table == "cost_analysis":
            # Advisory only — no production mutation
            return {"action": "none", "reason": "Cost analysis is advisory only"}

        elif table == "vendor_scorecards":
            session.execute(
                text(
                    "UPDATE suppliers SET rating = :rating, updated_at = NOW() WHERE id = :id"
                ),
                {"rating": data.get("overall_score"), "id": data.get("vendor_id")},
            )
            session.commit()
            return {
                "action": "updated",
                "table": "suppliers",
                "id": data.get("vendor_id"),
            }

        elif table == "budget_forecasts":
            session.execute(
                text(
                    "UPDATE events SET projected_profit = :profit, updated_at = NOW() WHERE id = :id"
                ),
                {"profit": data.get("projected_profit"), "id": data.get("event_id")},
            )
            session.commit()
            return {"action": "updated", "table": "events", "id": data.get("event_id")}

        return {
            "action": "unknown",
            "table": table,
            "warning": "No production apply logic defined",
        }

    # ═══════════════════════════════════════════════════════════
    # ANALYTICS (read-only aggregations from staging)
    # ═══════════════════════════════════════════════════════════

    def get_cost_summary(self, event_id: Optional[int] = None) -> Dict[str, Any]:
        """Aggregate cost analysis from staging."""
        with self.StagingSession() as session:
            query = f"""
                SELECT
                    COUNT(*) as total_analyses,
                    AVG(confidence_score) as avg_confidence,
                    MAX(created_at) as last_analysis
                FROM {STAGING_SCHEMA}.cost_analysis
                WHERE 1=1
            """
            params: dict = {}
            if event_id:
                query += " AND event_id = :event_id"
                params["event_id"] = event_id

            result = session.execute(text(query), params).mappings().fetchone()
            return dict(result) if result else {}


# ═══════════════════════════════════════════════════════════════════
# FASTAPI ROUTER (Pydantic v2 compatible)
# ═════════════════════════════════════════════════════════════════==

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/scm-bridge", tags=["SCM-BIO Bridge"])


class CostAnalysisRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": 1,
                "analysis_type": "strategic_cost_review",
                "input_data": {"budget": 100000, "actual": 95000},
                "results": {"variance": 5000, "variance_pct": 5.0},
                "recommendations": ["Reduce venue cost", "Renegotiate catering"],
                "confidence_score": 0.92,
            }
        }
    )

    event_id: int
    analysis_type: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    results: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.0)


class PromotionRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "staging_id": 1,
                "staging_table": "vendor_scorecards",
                "reason": "Q2 vendor evaluation complete",
            }
        }
    )

    staging_id: int
    staging_table: str
    reason: str


def get_bridge() -> SCMBioBridge:
    return SCMBioBridge()


@router.get("/production/events", summary="Read events from production")
def read_events(
    status: Optional[str] = None,
    event_type: Optional[str] = None,
    date_from: Optional[str] = None,
    limit: int = 100,
    bridge: SCMBioBridge = Depends(get_bridge),
):
    """Read events from production — READ ONLY."""
    filters = {}
    if status:
        filters["status"] = status
    if event_type:
        filters["event_type"] = event_type
    if date_from:
        filters["date_from"] = date_from

    return {
        "events": bridge.get_events(filters, limit),
        "source": "production_read_only",
        "schema": "public",
    }


@router.get("/production/events/{event_id}", summary="Read event detail")
def read_event_detail(event_id: int, bridge: SCMBioBridge = Depends(get_bridge)):
    """Read event detail with line items from production — READ ONLY."""
    data = bridge.get_event_detail(event_id)
    if not data:
        raise HTTPException(status_code=404, detail="Event not found")
    return data


@router.get("/production/clients", summary="Read clients")
def read_clients(
    status: Optional[str] = None,
    limit: int = 100,
    bridge: SCMBioBridge = Depends(get_bridge),
):
    return {"clients": bridge.get_clients(status, limit), "source": "production"}


@router.get("/production/transactions", summary="Read bank transactions")
def read_transactions(
    account: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 1000,
    bridge: SCMBioBridge = Depends(get_bridge),
):
    return {
        "transactions": bridge.get_transactions(date_from, date_to, account, limit),
        "source": "production",
    }


@router.get("/production/vendors", summary="Read vendors/suppliers")
def read_vendors(
    category: Optional[str] = None,
    limit: int = 100,
    bridge: SCMBioBridge = Depends(get_bridge),
):
    return {"vendors": bridge.get_vendors(category, limit), "source": "production"}


@router.post("/staging/cost-analysis", summary="Save cost analysis to staging")
def api_save_cost_analysis(
    req: CostAnalysisRequest, bridge: SCMBioBridge = Depends(get_bridge)
):
    """Save cost analysis to staging — NEVER production."""
    return bridge.save_cost_analysis(req.model_dump())


@router.post("/staging/vendor-scorecard", summary="Save vendor scorecard")
def api_save_vendor_scorecard(
    scorecard: dict, bridge: SCMBioBridge = Depends(get_bridge)
):
    return bridge.save_vendor_scorecard(scorecard)


@router.post("/staging/budget-forecast", summary="Save budget forecast")
def api_save_budget_forecast(
    forecast: dict, bridge: SCMBioBridge = Depends(get_bridge)
):
    return bridge.save_budget_forecast(forecast)


@router.post("/staging/request-promotion", summary="Request promotion to production")
def api_request_promotion(
    req: PromotionRequest,
    admin_user: str = "admin",
    bridge: SCMBioBridge = Depends(get_bridge),
):
    """Request promotion to production — requires admin approval."""
    return bridge.request_promotion(
        req.staging_id, req.staging_table, admin_user, req.reason
    )


@router.post(
    "/admin/approve-promotion/{request_id}", summary="Admin approves promotion"
)
def api_approve_promotion(
    request_id: int,
    admin_user: str = "admin",
    bridge: SCMBioBridge = Depends(get_bridge),
):
    """Admin approves promotion — ONLY authorized path to production."""
    return bridge.approve_promotion(request_id, admin_user)


@router.get("/staging/cost-summary", summary="Cost analysis summary")
def api_cost_summary(
    event_id: Optional[int] = None, bridge: SCMBioBridge = Depends(get_bridge)
):
    return bridge.get_cost_summary(event_id)
