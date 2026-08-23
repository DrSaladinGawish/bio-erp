"""
Empty-Module Production Models — 12 tables matching actual DB schemas.
Column name mapping: `ModelAttr = Column("db_column", Type, ...)` so routers
use logical names while querying actual DB columns.
"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from .models import IncentiveBase


class GrnHeader(IncentiveBase):
    __tablename__ = "grn_headers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    grn_no = Column("grn_number", String(50), index=True)
    grn_date = Column(Date)
    po_id = Column(Integer, index=True)
    vendor_id = Column("supplier_id", Integer, index=True)
    event_id = Column(Integer, index=True)
    received_by = Column(String(100))
    warehouse = Column("warehouse_location", String(100))
    status = Column(String(20), default="DRAFT")
    notes = Column(Text)
    total_qty = Column(Float, default=0.0)
    total_value = Column(Float, default=0.0)
    branch_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class GrnLine(IncentiveBase):
    __tablename__ = "grn_lines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    grn_id = Column(Integer, ForeignKey("grn_headers.id", ondelete="CASCADE"), index=True)
    line_no = Column(Integer)
    item_code = Column(String(50))
    description = Column(Text)
    ordered_qty = Column(Float, default=0.0)
    received_qty = Column(Float, default=0.0)
    rejected_qty = Column(Float, default=0.0)
    uom = Column(String(10), default="EA")
    unit_cost = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)
    account_code = Column(String(20))
    cost_center = Column(String(30))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class CostAllocation(IncentiveBase):
    __tablename__ = "cost_allocations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cost_center_id = Column(Integer, index=True)
    cost_center = Column(String(50))
    period = Column(String(10), index=True)
    category = Column("cost_type", String(50), index=True)
    amount = Column(Float, default=0.0)
    amount_egp = Column(Float, default=0.0)
    currency = Column(String(3), default="EGP")
    allocation_base = Column(String(100))
    base_quantity = Column(Float)
    rate_per_unit = Column(Float)
    is_actual = Column(Boolean, default=False)
    event_id = Column(Integer, index=True)
    pnr_id = Column(Integer, index=True)
    vendor_id = Column(Integer)
    description = Column(Text)
    notes = Column(Text)
    status = Column(String(20), default="DRAFT")
    alloc_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class EventBudgetLine(IncentiveBase):
    __tablename__ = "event_budget_lines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False)
    category = Column("section", String(50), index=True)
    planned_amount = Column(Float, default=0.0)
    actual_amount = Column(Float, default=0.0)
    committed_amount = Column(Float, default=0.0)
    pnr_id = Column(Integer, index=True)
    currency_id = Column(Integer)
    conversion_rate = Column(Float, default=1.0)
    amount_egp = Column(Float, default=0.0)
    notes = Column("description", String(200))
    quantity = Column(Float, default=0.0)
    unit_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    markup_percent = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    budget_version = Column(Integer, default=1)
    revision_reason = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class BudgetCategory(IncentiveBase):
    __tablename__ = "budget_categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column("category_code", String(30), unique=True, index=True)
    parent_id = Column(Integer)
    description = Column(String(200))
    default_coa_id = Column(Integer)
    name_en = Column(String(200))
    name_ar = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class BudgetLine(IncentiveBase):
    __tablename__ = "budget_lines"
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column("cost_center_id", Integer, index=True)
    category_id = Column("coa_account_id", Integer, index=True)
    fiscal_year = Column("budget_period_id", Integer, index=True)
    planned_amount = Column("budgeted_amount", Float, default=0.0)
    approved_amount = Column(Float, default=0.0)
    actual_amount = Column(Float, default=0.0)
    committed_amount = Column(Float, default=0.0)
    branch_id = Column(Integer)
    status = Column(String(20), default="DRAFT")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class BscObjective(IncentiveBase):
    __tablename__ = "bsc_objectives"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column("bsc_id", Integer, index=True)
    perspective = Column(String(30), index=True)
    name_en = Column("objective_name", String(200))
    weight = Column(Float, default=0.0)
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class BscIndicator(IncentiveBase):
    __tablename__ = "bsc_indicators"
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column("bsc_id", Integer, index=True)
    objective_id = Column(Integer, ForeignKey("bsc_objectives.id"), index=True)
    perspective = Column(String(30), index=True)
    name_en = Column("indicator_name", String(200))
    formula = Column(String(200))
    target_value = Column(Float)
    actual_value = Column(Float)
    score = Column(Float, default=0.0)
    weight = Column(Float, default=0.0)
    uom = Column(String(20))
    frequency = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class NeuralPrediction(IncentiveBase):
    __tablename__ = "neural_predictions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_name = Column("prediction_key", String(100), index=True)
    prediction_type = Column(String(50), index=True)
    predicted_value = Column(Float)
    confidence = Column(Float)
    actual_value = Column(Float)
    features_snapshot = Column(Text)
    model_version = Column(String(50))
    prediction_date = Column(DateTime)
    metadata_json = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class ApprovalRule(IncentiveBase):
    __tablename__ = "approval_rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    module = Column(String(50), index=True)
    document_type = Column(String(50), index=True)
    min_amount = Column(Float, default=0.0)
    max_amount = Column(Float)
    role_id = Column(Integer)
    user_id = Column(Integer)
    sequence = Column(Integer, default=1)
    priority = Column(Integer, default=500)
    approver_role = Column(String(100))
    is_mandatory = Column(Boolean, default=True)
    can_delegate = Column(Boolean, default=False)
    escalation_hours = Column(Integer)
    escalation_role_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class ApprovalInstance(IncentiveBase):
    __tablename__ = "approval_instances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    module = Column("document_type", String(50), index=True)
    document_id = Column(Integer)
    document_number = Column(String(100))
    requested_by = Column("requester_id", Integer)
    amount = Column("total_amount", Float, default=0.0)
    status = Column(String(20), default="PENDING")
    current_step = Column(Integer, default=1)
    total_steps = Column(Integer, default=1)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class ApprovalStep(IncentiveBase):
    __tablename__ = "approval_steps"
    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("approval_instances.id", ondelete="CASCADE"), index=True)
    sequence = Column(Integer)
    rule_id = Column(Integer)
    approver_id = Column(Integer)
    role_id = Column(Integer)
    status = Column(String(20), default="PENDING")
    decision = Column(String(20))
    comments = Column(Text)
    acted_at = Column(DateTime)
    due_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


EXTRA_PRODUCTION_MODELS = [
    GrnHeader, GrnLine, CostAllocation, EventBudgetLine,
    BudgetCategory, BudgetLine,
    BscObjective, BscIndicator,
    NeuralPrediction,
    ApprovalRule, ApprovalInstance, ApprovalStep,
]

__all__ = [
    "GrnHeader", "GrnLine", "CostAllocation", "EventBudgetLine",
    "BudgetCategory", "BudgetLine",
    "BscObjective", "BscIndicator",
    "NeuralPrediction",
    "ApprovalRule", "ApprovalInstance", "ApprovalStep",
    "EXTRA_PRODUCTION_MODELS",
]
