"""add_manufacturing_tables

Revision ID: mfg_001
Revises: <REPLACE WITH YOUR EXISTING BASE REVISION ID>
Create Date: 2025-01-01 00:00:00.000000

ACTION REQUIRED:
    Replace the `down_revision` value below with the actual revision ID of
    your most recent Bio-ERP migration. Run: flask db heads

    Then apply: flask db upgrade mfg_001

Downgrade:
    flask db downgrade <base_revision>
    Drops ONLY mfg_* tables and the two nullable Cell workcenter columns.
    Never touches: users, roles, permissions, cells (core), organs,
                   audit_logs, companies, or any other Bio-ERP table.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision    = "mfg_001"
down_revision = None  # Requires Clarification: replace with your base revision ID
branch_labels = ("manufacturing",)
depends_on    = None


def upgrade() -> None:
    # ── mfg_product ──────────────────────────────────────────────────
    op.create_table(
        "mfg_product",
        sa.Column("id",           sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id",   sa.BigInteger, nullable=False, index=True),
        sa.Column("sku",          sa.String(50),  nullable=False),
        sa.Column("name",         sa.String(255), nullable=False),
        sa.Column("product_type", sa.String(20),  nullable=False),
        sa.Column("unit_cost",    sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("uom",          sa.String(10),  nullable=False, server_default="pcs"),
        sa.Column("description",  sa.Text,        nullable=True),
        sa.Column("created_at",   sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",   sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("version",      sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("company_id", "sku", name="uq_mfg_product_company_sku"),
        sa.CheckConstraint("product_type IN ('RAW_MATERIAL','FINISHED_GOOD')",
                           name="ck_mfg_product_type"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_mfg_product_cost_positive"),
    )
    op.create_index("ix_mfg_product_company_type", "mfg_product",
                    ["company_id", "product_type", "deleted_at"])

    # ── mfg_bom ──────────────────────────────────────────────────────
    op.create_table(
        "mfg_bom",
        sa.Column("id",         sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.BigInteger,
                  sa.ForeignKey("mfg_product.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_active",  sa.Boolean, nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version",    sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("product_id", name="uq_mfg_bom_product"),
    )

    # ── mfg_bom_line ─────────────────────────────────────────────────
    op.create_table(
        "mfg_bom_line",
        sa.Column("id",           sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("bom_id",       sa.BigInteger,
                  sa.ForeignKey("mfg_bom.id", ondelete="CASCADE"), nullable=False),
        sa.Column("material_id",  sa.BigInteger,
                  sa.ForeignKey("mfg_product.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("qty_required", sa.Numeric(18, 4), nullable=False),
        sa.Column("uom",          sa.String(10), nullable=False, server_default="pcs"),
        sa.Column("sort_order",   sa.Integer,    nullable=False, server_default="0"),
        sa.UniqueConstraint("bom_id", "material_id", name="uq_mfg_bom_line_material"),
        sa.CheckConstraint("qty_required > 0", name="ck_mfg_bom_line_qty_positive"),
    )

    # ── mfg_production_order ─────────────────────────────────────────
    op.create_table(
        "mfg_production_order",
        sa.Column("id",              sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id",      sa.BigInteger, nullable=False, index=True),
        sa.Column("po_number",       sa.String(20),  nullable=False),
        sa.Column("product_id",      sa.BigInteger,
                  sa.ForeignKey("mfg_product.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("planned_qty",     sa.Numeric(18, 4), nullable=False),
        sa.Column("actual_qty",      sa.Numeric(18, 4), nullable=True),
        sa.Column("uom",             sa.String(10),  nullable=False, server_default="pcs"),
        sa.Column("status",          sa.String(20),  nullable=False, server_default="DRAFT"),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_end",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by",      sa.BigInteger, nullable=True),
        sa.Column("released_by",     sa.BigInteger, nullable=True),
        sa.Column("released_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by",       sa.BigInteger, nullable=True),
        sa.Column("closed_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes",           sa.Text, nullable=True),
        sa.Column("created_at",      sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",      sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("version",         sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("company_id", "po_number", name="uq_mfg_po_company_number"),
        sa.CheckConstraint(
            "status IN ('DRAFT','RELEASED','IN_PROGRESS','COMPLETED','CLOSED')",
            name="ck_mfg_po_status",
        ),
        sa.CheckConstraint("planned_qty > 0", name="ck_mfg_po_qty_positive"),
    )
    op.create_index("ix_mfg_po_company_status", "mfg_production_order",
                    ["company_id", "status", "deleted_at"])

    # ── mfg_po_raw_material ──────────────────────────────────────────
    op.create_table(
        "mfg_po_raw_material",
        sa.Column("id",            sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("po_id",         sa.BigInteger,
                  sa.ForeignKey("mfg_production_order.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("material_id",   sa.BigInteger,
                  sa.ForeignKey("mfg_product.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("qty_planned",   sa.Numeric(18, 4), nullable=False),
        sa.Column("qty_issued",    sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("qty_consumed",  sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("uom",           sa.String(10),  nullable=False, server_default="pcs"),
        sa.Column("sort_order",    sa.Integer,     nullable=False, server_default="0"),
        sa.Column("material_code", sa.String(50),  nullable=True),
        sa.Column("material_name", sa.String(255), nullable=True),
        sa.UniqueConstraint("po_id", "material_id", name="uq_mfg_porm_po_material"),
        sa.CheckConstraint("qty_planned >= 0",  name="ck_mfg_porm_planned_positive"),
        sa.CheckConstraint("qty_issued >= 0",   name="ck_mfg_porm_issued_positive"),
        sa.CheckConstraint("qty_consumed >= 0", name="ck_mfg_porm_consumed_positive"),
    )

    # ── mfg_po_operation ─────────────────────────────────────────────
    op.create_table(
        "mfg_po_operation",
        sa.Column("id",            sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("po_id",         sa.BigInteger,
                  sa.ForeignKey("mfg_production_order.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("op_sequence",   sa.Integer,    nullable=False),
        sa.Column("op_code",       sa.String(50), nullable=True),
        sa.Column("op_name",       sa.String(255), nullable=False),
        sa.Column("workcenter_id", sa.BigInteger, nullable=True),
        sa.Column("performed_by",  sa.String(100), nullable=True),
        sa.Column("started_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("status",        sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("skip_reason",   sa.Text, nullable=True),
        sa.UniqueConstraint("po_id", "op_sequence", name="uq_mfg_pop_po_sequence"),
        sa.CheckConstraint(
            "status IN ('PENDING','IN_PROGRESS','COMPLETED','SKIPPED')",
            name="ck_mfg_pop_status",
        ),
        sa.CheckConstraint("op_sequence > 0", name="ck_mfg_pop_sequence_positive"),
    )
    op.create_index("ix_mfg_pop_po_status", "mfg_po_operation", ["po_id", "status"])

    # ── mfg_po_transaction ───────────────────────────────────────────
    op.create_table(
        "mfg_po_transaction",
        sa.Column("id",             sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("po_id",          sa.BigInteger,
                  sa.ForeignKey("mfg_production_order.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("tx_type",        sa.String(20),  nullable=False),
        sa.Column("reference_line", sa.BigInteger,  nullable=True),
        sa.Column("qty",            sa.Numeric(18, 4), nullable=False),
        sa.Column("uom",            sa.String(10),  nullable=False),
        sa.Column("tx_timestamp",   sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("posted_by",      sa.String(100), nullable=False),
        sa.Column("notes",          sa.Text,        nullable=True),
        sa.Column("prev_hash",      sa.String(64),  nullable=True),
        sa.Column("chain_hash",     sa.String(64),  nullable=True),
        sa.CheckConstraint(
            "tx_type IN ('RM_ISSUE','RM_CONSUME','FG_RECEIPT','WIP_MOVE')",
            name="ck_mfg_potx_type",
        ),
        sa.CheckConstraint("qty > 0", name="ck_mfg_potx_qty_positive"),
    )
    op.create_index("ix_mfg_potx_po_type", "mfg_po_transaction", ["po_id", "tx_type"])

    # ── Extend existing Cell table with workcenter columns ───────────
    # These are NULLABLE so existing Cell rows are unaffected.
    op.add_column("cells",  # Requires Clarification: confirm your Cell table name
                  sa.Column("workcenter_department", sa.String(100), nullable=True))
    op.add_column("cells",
                  sa.Column("cost_rate_hour", sa.Numeric(18, 4), nullable=True))


def downgrade() -> None:
    """
    DROP only mfg_* tables and the workcenter columns added to Cell.
    NEVER drops: users, cells (core rows), organs, audit_logs, companies.
    """
    # Remove workcenter extensions from Cell first (FK-safe order)
    try:
        op.drop_column("cells", "cost_rate_hour")
        op.drop_column("cells", "workcenter_department")
    except Exception:
        pass  # Column may not exist if upgrade was partial

    # Drop mfg tables in reverse FK dependency order
    op.drop_index("ix_mfg_potx_po_type",      table_name="mfg_po_transaction")
    op.drop_table("mfg_po_transaction")

    op.drop_index("ix_mfg_pop_po_status",     table_name="mfg_po_operation")
    op.drop_table("mfg_po_operation")

    op.drop_table("mfg_po_raw_material")

    op.drop_index("ix_mfg_po_company_status", table_name="mfg_production_order")
    op.drop_table("mfg_production_order")

    op.drop_table("mfg_bom_line")
    op.drop_table("mfg_bom")

    op.drop_index("ix_mfg_product_company_type", table_name="mfg_product")
    op.drop_table("mfg_product")
