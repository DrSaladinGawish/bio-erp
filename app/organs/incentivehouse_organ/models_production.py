"""
Production Models — Sales / Purchase / Events / Staff / Work Orders
====================================================================
Extension of ``models.py`` that adds the production-side tables the SAL,
PUR, EVN routers and the master-data loader need. These tables are
auto-created on first boot by ``main._ensure_tables_sync()`` (it calls
``IncentiveBase.metadata.create_all``), so no separate Alembic migration
is required for development. A migration ``002_production_tables`` can be
added later for production deploys.

Tables added (10):
  1.  vendors_mtbl         — vendor master
  2.  staff_mtbl           — staff / employees master
  3.  events               — event header records (PNR + venue + date)
  4.  work_orders          — operational work orders tied to events
  5.  staff_assignments    — staff ↔ work-order allocations
  6.  sales_invoices       — sales invoice header
  7.  sales_line_items     — sales invoice line items
  8.  purchase_orders      — purchase order header
  9.  vendor_invoices      — vendor invoice header
  10. budget_lines         — cost-centre budget lines

All tables share ``IncentiveBase`` from ``models.py`` so ``create_all``
picks them up automatically once this module is imported anywhere in the
process (the routers, the loader, and main.py all import it).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, Index,
)
from sqlalchemy.orm import relationship

from .models import IncentiveBase


# ──────────────────────────────────────────────────────────────────────
# 0. Master-data tables that were created by the Alembic migration
#    but were not previously exposed as ORM models
# ──────────────────────────────────────────────────────────────────────

class Client(IncentiveBase):
    __tablename__ = "clients_mtbl"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), index=True)
    name = Column(String(255))
    tax_id = Column(String(50))
    contact = Column(String(255))
    address = Column(Text)
    acc_key = Column(Integer)


class CostCenter(IncentiveBase):
    __tablename__ = "cost_centers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(255))
    type = Column(String(20), default="PRODUCTION")
    parent_id = Column(Integer)
    budget_limit = Column(Float, default=0.0)


class PnrRecord(IncentiveBase):
    __tablename__ = "pnr_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pnr_code = Column(String(50), nullable=False, unique=True, index=True)
    client_id = Column(Integer, index=True)
    event_date = Column(Date)
    venue = Column(String(255))
    status = Column(String(20), default="OPEN")
    gross_sales = Column(Float, default=0.0)
    currency = Column(String(3), default="EGP")


# ──────────────────────────────────────────────────────────────────────
# 1. Vendors master
# ──────────────────────────────────────────────────────────────────────

class Vendor(IncentiveBase):
    __tablename__ = "vendors_mtbl"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, index=True)
    name = Column(String(255), nullable=False)
    tax_id = Column(String(50))
    contact = Column(String(255))
    phone = Column(String(50))
    email = Column(String(255))
    address = Column(Text)
    category = Column(String(50))           # SUPPLIER / CONTRACTOR / BOTH
    payment_terms = Column(String(50))      # NET30 / NET45 / COD / etc.
    acc_key = Column(Integer)               # sub-ledger key
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# 2. Staff / employees master
# ──────────────────────────────────────────────────────────────────────

class Staff(IncentiveBase):
    __tablename__ = "staff_mtbl"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, index=True)
    name = Column(String(255), nullable=False)
    role = Column(String(50))               # EVENT_MGR / ACCOUNTANT / CREW
    department = Column(String(100))
    phone = Column(String(50))
    email = Column(String(255))
    hire_date = Column(Date)
    cost_center = Column(String(30))
    hourly_rate = Column(Float, default=0.0)
    active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# 3. Events (header — links to PNR + client)
# ──────────────────────────────────────────────────────────────────────

class Event(IncentiveBase):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_code = Column(String(50), unique=True, index=True, nullable=False)
    pnr_id = Column(Integer, index=True)
    client_id = Column(Integer, index=True)
    event_name = Column(String(255))
    event_date = Column(Date)
    end_date = Column(Date)
    venue = Column(String(255))
    city = Column(String(100))
    country = Column(String(50), default="EG")
    status = Column(String(20), default="OPEN")  # OPEN / CLOSED / CANCELLED
    budget = Column(Float, default=0.0)
    gross_sales = Column(Float, default=0.0)
    currency = Column(String(3), default="EGP")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# 4. Work orders (operational — under an event)
# ──────────────────────────────────────────────────────────────────────

class WorkOrder(IncentiveBase):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wo_code = Column(String(50), unique=True, index=True, nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), index=True)
    department = Column(String(50))         # PRODUCTION / LOGISTICS / etc.
    task = Column(String(255))
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String(20), default="PENDING")
    budget = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    currency = Column(String(3), default="EGP")
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# 5. Staff assignments (staff ↔ work-order)
# ──────────────────────────────────────────────────────────────────────

class StaffAssignment(IncentiveBase):
    __tablename__ = "staff_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    staff_id = Column(Integer, ForeignKey("staff_mtbl.id"), index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), index=True)
    event_id = Column(Integer, ForeignKey("events.id"), index=True)
    role = Column(String(50))                # LEAD / CREW / SUPERVISOR
    start_date = Column(Date)
    end_date = Column(Date)
    hours_planned = Column(Float, default=0.0)
    hours_actual = Column(Float, default=0.0)
    hourly_rate = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    currency = Column(String(3), default="EGP")
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# 6. Sales invoices (header)
# ──────────────────────────────────────────────────────────────────────

class SalesInvoice(IncentiveBase):
    __tablename__ = "sales_invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_no = Column(String(50), unique=True, index=True, nullable=False)
    invoice_date = Column(Date, index=True)
    client_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    pnr_id = Column(Integer, index=True)
    currency = Column(String(3), default="EGP")
    exchange_rate = Column(Float, default=1.0)
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    status = Column(String(20), default="OPEN")  # OPEN / PARTIAL / PAID / CANCELLED
    due_date = Column(Date)
    payment_terms = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# 7. Sales line items
# ──────────────────────────────────────────────────────────────────────

class SalesLineItem(IncentiveBase):
    __tablename__ = "sales_line_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("sales_invoices.id"), index=True)
    line_no = Column(Integer)
    item_code = Column(String(50))
    description = Column(Text)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    line_total = Column(Float, default=0.0)
    cost_center = Column(String(30))
    pnr_id = Column(Integer, index=True)
    account_code = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# 8. Purchase orders (header)
# ──────────────────────────────────────────────────────────────────────

class PurchaseOrder(IncentiveBase):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    po_no = Column(String(50), unique=True, index=True, nullable=False)
    po_date = Column(Date, index=True)
    vendor_id = Column(Integer, index=True)
    event_id = Column(Integer, index=True)
    pnr_id = Column(Integer, index=True)
    currency = Column(String(3), default="EGP")
    exchange_rate = Column(Float, default=1.0)
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    status = Column(String(20), default="OPEN")  # DRAFT / OPEN / APPROVED / RECEIVED / CLOSED
    expected_delivery = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# 9. Vendor invoices
# ──────────────────────────────────────────────────────────────────────

class VendorInvoice(IncentiveBase):
    __tablename__ = "vendor_invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_no = Column(String(50), unique=True, index=True, nullable=False)
    invoice_date = Column(Date, index=True)
    vendor_id = Column(Integer, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"), index=True)
    event_id = Column(Integer, index=True)
    pnr_id = Column(Integer, index=True)
    currency = Column(String(3), default="EGP")
    exchange_rate = Column(Float, default=1.0)
    subtotal = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    status = Column(String(20), default="OPEN")
    due_date = Column(Date)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# 10. Budget lines
# ──────────────────────────────────────────────────────────────────────

class BudgetLine(IncentiveBase):
    __tablename__ = "budget_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cost_center = Column(String(30), index=True)
    event_id = Column(Integer, index=True)
    fiscal_year = Column(Integer, index=True)
    fiscal_month = Column(Integer)
    category = Column(String(50))            # REVENUE / COST / CAPEX
    planned_amount = Column(Float, default=0.0)
    actual_amount = Column(Float, default=0.0)
    variance = Column(Float, default=0.0)
    currency = Column(String(3), default="EGP")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────
# Reconciliation-result table (used by recon_router for stored matches)
# ──────────────────────────────────────────────────────────────────────

class ReconMatch(IncentiveBase):
    """Stored reconciliation matches produced by the recon engine."""
    __tablename__ = "recon_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    module = Column(String(10), index=True)        # BNK / SAL / PUR / EVN / ENV
    source_txn_id = Column(String(50), index=True)
    target_txn_id = Column(String(50), index=True)
    source_amount = Column(Float, default=0.0)
    target_amount = Column(Float, default=0.0)
    variance = Column(Float, default=0.0)
    match_type = Column(String(30))                # exact_amount_date / reference_match / fuzzy
    confidence = Column(Float, default=0.0)
    match_status = Column(String(20), default="MATCHED")  # MATCHED / VARIANCE / UNMATCHED
    rule_applied = Column(String(100))
    matched_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(String(50))
    notes = Column(Text)


# ──────────────────────────────────────────────────────────────────────
# Convenience: tuple of all model classes for metadata.create_all
# ──────────────────────────────────────────────────────────────────────

ALL_PRODUCTION_MODELS = (
    Client, CostCenter, PnrRecord,
    Vendor, Staff, Event, WorkOrder, StaffAssignment,
    SalesInvoice, SalesLineItem, PurchaseOrder,
    VendorInvoice, BudgetLine, ReconMatch,
)


# ──────────────────────────────────────────────────────────────────────
# Reverse: production-table → ORM class lookup for the routers
# ──────────────────────────────────────────────────────────────────────

PRODUCTION_MODEL_MAP = {
    "clients_mtbl": Client,
    "cost_centers": CostCenter,
    "pnr_records": PnrRecord,
    "vendors_mtbl": Vendor,
    "staff_mtbl": Staff,
    "events": Event,
    "work_orders": WorkOrder,
    "staff_assignments": StaffAssignment,
    "sales_invoices": SalesInvoice,
    "sales_line_items": SalesLineItem,
    "purchase_orders": PurchaseOrder,
    "vendor_invoices": VendorInvoice,
    "budget_lines": BudgetLine,
    "recon_matches": ReconMatch,
}


__all__ = [
    "Client", "CostCenter", "PnrRecord",
    "Vendor", "Staff", "Event", "WorkOrder", "StaffAssignment",
    "SalesInvoice", "SalesLineItem", "PurchaseOrder",
    "VendorInvoice", "BudgetLine", "ReconMatch",
    "ALL_PRODUCTION_MODELS", "PRODUCTION_MODEL_MAP",
]
