"""initial organ tables - creates the 27 IncentiveHouse tables on first boot

Revision ID: 001_initial_organ_tables
Revises:
Create Date: 2026-06-02 19:34:00.000000

This migration creates the complete schema for the IncentiveHouse organ
(5 *_staging tables + 1 audit log + 21 master/lifecycle/recon/config
tables) so the Docker container can come up on a clean database with
just ``alembic upgrade head``.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial_organ_tables"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Audit log
    op.create_table(
        "incentivehouse_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("module", sa.String(length=20), nullable=False),
        sa.Column("source_file", sa.String(length=500)),
        sa.Column("total_rows", sa.Integer(), server_default="0"),
        sa.Column("passed", sa.Integer(), server_default="0"),
        sa.Column("warnings", sa.Integer(), server_default="0"),
        sa.Column("failed", sa.Integer(), server_default="0"),
        sa.Column("staged", sa.Integer(), server_default="0"),
        sa.Column("dry_run", sa.Integer(), server_default="1"),
        sa.Column("summary", sa.Text()),
        sa.Column("errors_json", sa.Text()),
        sa.Column("started_at", sa.String(length=30)),
        sa.Column("completed_at", sa.String(length=30)),
    )

    # 2-6. *_staging tables (Bnk, Sal, Pur, Evn, Env)
    staging_columns = [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(length=50), index=True),
        sa.Column("transaction_id", sa.String(length=50), index=True),
        sa.Column("transaction_date", sa.String(length=20)),
        sa.Column("account_code", sa.String(length=20)),
        sa.Column("description", sa.Text()),
        sa.Column("debit_amount", sa.Float()),
        sa.Column("credit_amount", sa.Float()),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
        sa.Column("exchange_rate", sa.Float(), server_default="1.0"),
        sa.Column("sub_led_code", sa.Integer()),
        sa.Column("pnr_id", sa.Integer()),
        sa.Column("client_id", sa.Integer()),
        sa.Column("cost_center", sa.String(length=30)),
        sa.Column("validation_status", sa.String(length=10), server_default="PASS"),
        sa.Column("validation_errors", sa.Text()),
        sa.Column("source_file", sa.String(length=200)),
        sa.Column("source_row", sa.Integer()),
        sa.Column("staged_at", sa.String(length=30)),
    ]
    for table in ("bnk_staging", "sal_staging", "pur_staging", "evn_staging", "env_staging"):
        op.create_table(table, *staging_columns)

    # 7-13. Pipeline lifecycle logs
    op.create_table(
        "extraction_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("module", sa.String(length=20), nullable=False),
        sa.Column("source_file", sa.String(length=255)),
        sa.Column("user_id", sa.String(length=100)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("extracted_at", sa.String(length=30)),
    )
    op.create_table(
        "validation_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("extract_id", sa.Integer()),
        sa.Column("user_id", sa.String(length=100)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("quality_score", sa.Float()),
        sa.Column("validated_at", sa.String(length=30)),
    )
    op.create_table(
        "staging_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("validate_id", sa.Integer()),
        sa.Column("target_table", sa.String(length=100)),
        sa.Column("user_id", sa.String(length=100)),
        sa.Column("snapshot_id", sa.String(length=100)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("staged_at", sa.String(length=30)),
    )
    op.create_table(
        "reconcile_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("stage_id", sa.Integer()),
        sa.Column("module", sa.String(length=20)),
        sa.Column("user_id", sa.String(length=100)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("total_records", sa.Integer(), server_default="0"),
        sa.Column("reconciled_count", sa.Integer(), server_default="0"),
        sa.Column("mismatch_count", sa.Integer(), server_default="0"),
        sa.Column("unmatched_count", sa.Integer(), server_default="0"),
        sa.Column("reconciled_at", sa.String(length=30)),
    )
    op.create_table(
        "approval_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recon_id", sa.Integer()),
        sa.Column("approver_id", sa.String(length=100)),
        sa.Column("approval_level", sa.String(length=20)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("approved_at", sa.String(length=30)),
    )
    op.create_table(
        "promotion_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("approve_id", sa.Integer()),
        sa.Column("user_id", sa.String(length=100)),
        sa.Column("rollback_token", sa.String(length=100)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("promoted_at", sa.String(length=30)),
    )
    op.create_table(
        "observe_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("promote_id", sa.Integer()),
        sa.Column("user_id", sa.String(length=100)),
        sa.Column("status", sa.String(length=20)),
        sa.Column("metrics", sa.Text()),
        sa.Column("observed_at", sa.String(length=30)),
    )

    # 14-15. Reconciliation
    op.create_table(
        "bnk_reconciliation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.String(length=50)),
        sa.Column("check_book_id", sa.Integer()),
        sa.Column("check_book_name", sa.String(length=100)),
        sa.Column("bank_amount", sa.Float()),
        sa.Column("gl_amount", sa.Float()),
        sa.Column("variance", sa.Float()),
        sa.Column("recon_status", sa.String(length=20), server_default="PENDING"),
        sa.Column("user_sub_led", sa.String(length=100)),
        sa.Column("user_type", sa.String(length=50)),
        sa.Column("user_keyword", sa.String(length=200)),
        sa.Column("user_notes", sa.Text()),
    )
    op.create_table(
        "bnk_trnx_staging",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.String(length=50)),
        sa.Column("check_book_id", sa.String(length=20)),
        sa.Column("transaction_date", sa.String(length=20)),
        sa.Column("narration", sa.Text()),
        sa.Column("debit", sa.Float(), server_default="0"),
        sa.Column("credit", sa.Float(), server_default="0"),
        sa.Column("amount", sa.Float(), server_default="0"),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
        sa.Column("_extracted_at", sa.String(length=30)),
        sa.Column("_batch_id", sa.String(length=50)),
        sa.Column("_module", sa.String(length=10)),
    )

    # 16-21. Master data
    op.create_table(
        "clients_mtbl",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=20), index=True),
        sa.Column("name", sa.String(length=255)),
        sa.Column("tax_id", sa.String(length=50)),
        sa.Column("contact", sa.String(length=255)),
        sa.Column("address", sa.Text()),
        sa.Column("acc_key", sa.Integer()),
    )
    op.create_table(
        "cost_centers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=20), nullable=False, unique=True),
        sa.Column("name", sa.String(length=255)),
        sa.Column("type", sa.String(length=20), server_default="PRODUCTION"),
        sa.Column("parent_id", sa.Integer()),
        sa.Column("budget_limit", sa.Float(), server_default="0"),
    )
    op.create_table(
        "cheque_books",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("bank_account_id", sa.Integer()),
        sa.Column("cheque_book_number", sa.String(length=50)),
        sa.Column("start_number", sa.Integer(), server_default="0"),
        sa.Column("end_number", sa.Integer(), server_default="0"),
        sa.Column("current_number", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE"),
        sa.Column("issue_date", sa.String(length=20)),
        sa.Column("branch_id", sa.Integer()),
    )
    op.create_table(
        "sub_ledger_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sub_led_code", sa.Integer(), nullable=False, unique=True),
        sa.Column("description", sa.String(length=255)),
        sa.Column("account_code", sa.String(length=20)),
        sa.Column("active", sa.Integer(), server_default="1"),
    )
    op.create_table(
        "trnx_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transaction_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("transaction_type", sa.String(length=20)),
        sa.Column("module", sa.String(length=10)),
        sa.Column("description", sa.String(length=255)),
    )
    op.create_table(
        "pnr_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("pnr_code", sa.String(length=50), nullable=False, unique=True),
        sa.Column("client_id", sa.Integer()),
        sa.Column("event_date", sa.String(length=20)),
        sa.Column("venue", sa.String(length=255)),
        sa.Column("status", sa.String(length=20), server_default="OPEN"),
        sa.Column("gross_sales", sa.Float(), server_default="0"),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
    )

    # 22-27. Config / meta / operational
    op.create_table(
        "source_paths",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("module", sa.String(length=10), nullable=False),
        sa.Column("key", sa.String(length=50), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("description", sa.String(length=255)),
        sa.Column("sheet", sa.String(length=100)),
        sa.Column("split_to", sa.Text()),
    )
    op.create_table(
        "mapping_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("module", sa.String(length=10), nullable=False),
        sa.Column("source_column", sa.String(length=100), nullable=False),
        sa.Column("target_field", sa.String(length=100), nullable=False),
        sa.Column("transform", sa.String(length=100)),
        sa.Column("default_value", sa.String(length=255)),
    )
    op.create_table(
        "validation_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("module", sa.String(length=10), nullable=False),
        sa.Column("field", sa.String(length=100), nullable=False),
        sa.Column("rule_type", sa.String(length=20), nullable=False),
        sa.Column("expression", sa.String(length=500)),
        sa.Column("severity", sa.String(length=10), server_default="ERROR"),
    )
    op.create_table(
        "snapshot_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_id", sa.String(length=100), nullable=False, index=True),
        sa.Column("target_table", sa.String(length=100)),
        sa.Column("row_count", sa.Integer(), server_default="0"),
        sa.Column("payload", sa.Text()),
        sa.Column("created_by", sa.String(length=50), server_default="api"),
        sa.Column("created_at", sa.String(length=30)),
    )
    op.create_table(
        "error_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.String(length=50), index=True),
        sa.Column("module", sa.String(length=10)),
        sa.Column("source_file", sa.String(length=500)),
        sa.Column("source_row", sa.Integer()),
        sa.Column("error_type", sa.String(length=50)),
        sa.Column("message", sa.Text()),
        sa.Column("context", sa.Text()),
        sa.Column("created_at", sa.String(length=30)),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(length=50), nullable=False, index=True),
        sa.Column("module", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ready"),
        sa.Column("last_run", sa.String(length=30)),
        sa.Column("payload", sa.Text()),
        sa.Column("started_at", sa.String(length=30)),
        sa.Column("finished_at", sa.String(length=30)),
    )


    # ── Production tables (used by SAL, PUR, EVN, ENV, RECON routers) ──

    op.create_table(
        "bnk_transactions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_code", sa.String(length=20), index=True),
        sa.Column("currency_code", sa.String(length=3), server_default="EGP"),
        sa.Column("txn_date", sa.DateTime()),
        sa.Column("txn_type", sa.String(length=50)),
        sa.Column("description", sa.String(length=500)),
        sa.Column("reference_no", sa.String(length=50), index=True),
        sa.Column("debit_amount", sa.Float(), server_default="0"),
        sa.Column("credit_amount", sa.Float(), server_default="0"),
        sa.Column("amount", sa.Float(), server_default="0"),
        sa.Column("sub_ledger_code", sa.String(length=20)),
        sa.Column("pnr_id", sa.Integer()),
        sa.Column("counterparty", sa.String(length=200)),
        sa.Column("is_reconciled", sa.Integer(), server_default="0"),
        sa.Column("is_flagged", sa.Integer(), server_default="0"),
        sa.Column("source", sa.String(length=50), server_default="excel_import"),
        sa.Column("row_hash", sa.String(length=64), unique=True),
        sa.Column("imported_at", sa.DateTime()),
    )
    op.create_table(
        "vendors_mtbl",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=20), unique=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("tax_id", sa.String(length=50)),
        sa.Column("contact", sa.String(length=255)),
        sa.Column("phone", sa.String(length=50)),
        sa.Column("email", sa.String(length=255)),
        sa.Column("address", sa.Text()),
        sa.Column("category", sa.String(length=50)),
        sa.Column("payment_terms", sa.String(length=50)),
        sa.Column("acc_key", sa.Integer()),
        sa.Column("active", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "staff_mtbl",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=20), unique=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50)),
        sa.Column("department", sa.String(length=100)),
        sa.Column("phone", sa.String(length=50)),
        sa.Column("email", sa.String(length=255)),
        sa.Column("hire_date", sa.Date()),
        sa.Column("cost_center", sa.String(length=30)),
        sa.Column("hourly_rate", sa.Float(), server_default="0"),
        sa.Column("active", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_code", sa.String(length=50), unique=True, index=True, nullable=False),
        sa.Column("pnr_id", sa.Integer(), index=True),
        sa.Column("client_id", sa.Integer(), index=True),
        sa.Column("event_name", sa.String(length=255)),
        sa.Column("event_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("venue", sa.String(length=255)),
        sa.Column("city", sa.String(length=100)),
        sa.Column("country", sa.String(length=50), server_default="EG"),
        sa.Column("status", sa.String(length=20), server_default="OPEN"),
        sa.Column("budget", sa.Float(), server_default="0"),
        sa.Column("gross_sales", sa.Float(), server_default="0"),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "work_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("wo_code", sa.String(length=50), unique=True, index=True, nullable=False),
        sa.Column("event_id", sa.Integer(), index=True),
        sa.Column("department", sa.String(length=50)),
        sa.Column("task", sa.String(length=255)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("status", sa.String(length=20), server_default="PENDING"),
        sa.Column("budget", sa.Float(), server_default="0"),
        sa.Column("actual_cost", sa.Float(), server_default="0"),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "staff_assignments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("staff_id", sa.Integer(), index=True),
        sa.Column("work_order_id", sa.Integer(), index=True),
        sa.Column("event_id", sa.Integer(), index=True),
        sa.Column("role", sa.String(length=50)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("hours_planned", sa.Float(), server_default="0"),
        sa.Column("hours_actual", sa.Float(), server_default="0"),
        sa.Column("hourly_rate", sa.Float(), server_default="0"),
        sa.Column("total_cost", sa.Float(), server_default="0"),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "sales_invoices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("invoice_no", sa.String(length=50), unique=True, index=True, nullable=False),
        sa.Column("invoice_date", sa.Date(), index=True),
        sa.Column("client_id", sa.Integer(), index=True),
        sa.Column("event_id", sa.Integer(), index=True),
        sa.Column("pnr_id", sa.Integer(), index=True),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
        sa.Column("exchange_rate", sa.Float(), server_default="1"),
        sa.Column("subtotal", sa.Float(), server_default="0"),
        sa.Column("tax_amount", sa.Float(), server_default="0"),
        sa.Column("total", sa.Float(), server_default="0"),
        sa.Column("paid_amount", sa.Float(), server_default="0"),
        sa.Column("status", sa.String(length=20), server_default="OPEN"),
        sa.Column("due_date", sa.Date()),
        sa.Column("payment_terms", sa.String(length=50)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "sales_line_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("invoice_id", sa.Integer(), index=True),
        sa.Column("line_no", sa.Integer()),
        sa.Column("item_code", sa.String(length=50)),
        sa.Column("description", sa.Text()),
        sa.Column("quantity", sa.Float(), server_default="1"),
        sa.Column("unit_price", sa.Float(), server_default="0"),
        sa.Column("discount", sa.Float(), server_default="0"),
        sa.Column("tax_rate", sa.Float(), server_default="0"),
        sa.Column("line_total", sa.Float(), server_default="0"),
        sa.Column("cost_center", sa.String(length=30)),
        sa.Column("pnr_id", sa.Integer(), index=True),
        sa.Column("account_code", sa.String(length=20)),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("po_no", sa.String(length=50), unique=True, index=True, nullable=False),
        sa.Column("po_date", sa.Date(), index=True),
        sa.Column("vendor_id", sa.Integer(), index=True),
        sa.Column("event_id", sa.Integer(), index=True),
        sa.Column("pnr_id", sa.Integer(), index=True),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
        sa.Column("exchange_rate", sa.Float(), server_default="1"),
        sa.Column("subtotal", sa.Float(), server_default="0"),
        sa.Column("tax_amount", sa.Float(), server_default="0"),
        sa.Column("total", sa.Float(), server_default="0"),
        sa.Column("status", sa.String(length=20), server_default="OPEN"),
        sa.Column("expected_delivery", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "vendor_invoices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("invoice_no", sa.String(length=50), unique=True, index=True, nullable=False),
        sa.Column("invoice_date", sa.Date(), index=True),
        sa.Column("vendor_id", sa.Integer(), index=True),
        sa.Column("po_id", sa.Integer(), index=True),
        sa.Column("event_id", sa.Integer(), index=True),
        sa.Column("pnr_id", sa.Integer(), index=True),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
        sa.Column("exchange_rate", sa.Float(), server_default="1"),
        sa.Column("subtotal", sa.Float(), server_default="0"),
        sa.Column("tax_amount", sa.Float(), server_default="0"),
        sa.Column("total", sa.Float(), server_default="0"),
        sa.Column("paid_amount", sa.Float(), server_default="0"),
        sa.Column("status", sa.String(length=20), server_default="OPEN"),
        sa.Column("due_date", sa.Date()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "budget_lines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cost_center", sa.String(length=30), index=True),
        sa.Column("event_id", sa.Integer(), index=True),
        sa.Column("fiscal_year", sa.Integer(), index=True),
        sa.Column("fiscal_month", sa.Integer()),
        sa.Column("category", sa.String(length=50)),
        sa.Column("planned_amount", sa.Float(), server_default="0"),
        sa.Column("actual_amount", sa.Float(), server_default="0"),
        sa.Column("variance", sa.Float(), server_default="0"),
        sa.Column("currency", sa.String(length=3), server_default="EGP"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_table(
        "recon_matches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("module", sa.String(length=10), index=True),
        sa.Column("source_txn_id", sa.String(length=50), index=True),
        sa.Column("target_txn_id", sa.String(length=50), index=True),
        sa.Column("source_amount", sa.Float(), server_default="0"),
        sa.Column("target_amount", sa.Float(), server_default="0"),
        sa.Column("variance", sa.Float(), server_default="0"),
        sa.Column("match_type", sa.String(length=30)),
        sa.Column("confidence", sa.Float(), server_default="0"),
        sa.Column("match_status", sa.String(length=20), server_default="MATCHED"),
        sa.Column("rule_applied", sa.String(length=100)),
        sa.Column("matched_at", sa.DateTime()),
        sa.Column("user_id", sa.String(length=50)),
        sa.Column("notes", sa.Text()),
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    for table in (
        "recon_matches", "budget_lines", "vendor_invoices",
        "purchase_orders", "sales_line_items", "sales_invoices",
        "staff_assignments", "work_orders", "events",
        "staff_mtbl", "vendors_mtbl", "bnk_transactions",
        "agent_runs", "error_logs", "snapshot_records",
        "validation_rules", "mapping_rules", "source_paths",
        "pnr_records", "trnx_keys", "sub_ledger_keys",
        "cheque_books", "cost_centers", "clients_mtbl",
        "bnk_trnx_staging", "bnk_reconciliation",
        "observe_log", "promotion_log", "approval_log",
        "reconcile_log", "staging_log", "validation_log",
        "extraction_log",
        "env_staging", "evn_staging", "pur_staging",
        "sal_staging", "bnk_staging",
        "incentivehouse_audit_log",
    ):
        op.drop_table(table)
