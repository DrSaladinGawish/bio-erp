"""
app/models_manufacturing.py
============================
Manufacturing domain models — add to existing app/models.py.

ACTION: Copy the classes below into your app/models.py after the existing
        entities (Cell, Organ, EventMaster, etc.). They share the same
        Base, CompanyTenantMixin, and AuditMixin.

Table prefix: mfg_* — no collision with existing tables.

Business rules enforced at DB level:
  - PORawMaterial: CHECK qty_issued <= qty_planned AND qty_consumed <= qty_planned
  - POOperation:   UNIQUE(po_id, op_sequence) — one slot per PO per step
  - MfgProduct:    UNIQUE(company_id, sku)
  - MfgBOMLine:    UNIQUE(bom_id, material_id) — no duplicate RM per BOM
  - POTransaction: INSERT-only — application enforces via service layer

All entities use:
  - CompanyTenantMixin  → company_id column + query filter
  - AuditMixin         → created_at, updated_at, deleted_at, version
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime,
    ForeignKey, Integer, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

# Import from your existing models.py:
# from app.models import Base, AuditMixin, CompanyTenantMixin
# Replace the two lines below with the actual import when merging.
from app.models import AuditMixin, Base, CompanyTenantMixin


# ═══════════════════════════════════════════════════════════════════
# Product master & BOM
# ═══════════════════════════════════════════════════════════════════

class MfgProduct(CompanyTenantMixin, AuditMixin, Base):
    """
    Product master — both raw materials (RM) and finished goods (FG).

    EventMaster is NOT used here: it represents calendar/event entities.
    MfgProduct is an inventory item with SKU, cost, and BOM linkage.
    """
    __tablename__  = "mfg_products"
    __table_args__ = (
        UniqueConstraint("company_id", "sku", name="uq_mfg_product_sku"),
        CheckConstraint("product_type IN ('RAW_MATERIAL','FINISHED_GOOD')",
                        name="ck_mfg_product_type"),
        CheckConstraint("unit_cost >= 0", name="ck_mfg_product_cost"),
    )

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    sku          = Column(String(50),  nullable=False)
    name         = Column(String(255), nullable=False)
    product_type = Column(String(20),  nullable=False)   # RAW_MATERIAL | FINISHED_GOOD
    unit_cost    = Column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    uom          = Column(String(10),  nullable=False, default="pcs")
    description  = Column(Text,        nullable=True)
    is_active    = Column(Boolean,     nullable=False, default=True)

    bom_as_parent   = relationship("MfgBOM",     back_populates="finished_product",
                                   foreign_keys="MfgBOM.product_id",
                                   cascade="all, delete-orphan")
    bom_lines_as_rm = relationship("MfgBOMLine",  back_populates="material",
                                   foreign_keys="MfgBOMLine.material_id")

    def __repr__(self) -> str:
        return f"<MfgProduct sku={self.sku!r} type={self.product_type}>"


class MfgBOM(CompanyTenantMixin, AuditMixin, Base):
    """
    Bill of Materials header.  One BOM per finished-good product.
    Revision-controlled via AuditMixin version column.
    """
    __tablename__  = "mfg_boms"
    __table_args__ = (
        UniqueConstraint("company_id", "product_id", name="uq_mfg_bom_product"),
    )

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id = Column(BigInteger, ForeignKey("mfg_products.id", ondelete="CASCADE"),
                        nullable=False)
    is_active  = Column(Boolean, nullable=False, default=True)

    finished_product = relationship("MfgProduct", back_populates="bom_as_parent",
                                    foreign_keys=[product_id])
    lines            = relationship("MfgBOMLine", back_populates="bom",
                                    cascade="all, delete-orphan",
                                    order_by="MfgBOMLine.sort_order")

    def __repr__(self) -> str:
        return f"<MfgBOM id={self.id} product_id={self.product_id}>"


class MfgBOMLine(AuditMixin, Base):
    """
    Single raw-material line within a BOM.
    Soft-deletes inherited from AuditMixin (deleted_at).
    """
    __tablename__  = "mfg_bom_lines"
    __table_args__ = (
        UniqueConstraint("bom_id", "material_id", name="uq_mfg_bom_line_material"),
        CheckConstraint("qty_required > 0", name="ck_mfg_bom_line_qty"),
    )

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    bom_id       = Column(BigInteger, ForeignKey("mfg_boms.id", ondelete="CASCADE"),
                          nullable=False)
    material_id  = Column(BigInteger, ForeignKey("mfg_products.id"), nullable=False)
    qty_required = Column(Numeric(18, 4), nullable=False)
    uom          = Column(String(10),     nullable=False, default="pcs")
    sort_order   = Column(Integer,        nullable=False, default=0)

    bom      = relationship("MfgBOM",    back_populates="lines")
    material = relationship("MfgProduct", back_populates="bom_lines_as_rm",
                            foreign_keys=[material_id])


# ═══════════════════════════════════════════════════════════════════
# Production Order (header)
# ═══════════════════════════════════════════════════════════════════

class MfgProductionOrder(CompanyTenantMixin, AuditMixin, Base):
    """
    Production Order header.

    po_number format: "#00001" — zero-padded 5-digit serial, unique per company.
    status lifecycle: DRAFT → RELEASED → IN_PROGRESS → COMPLETED → CLOSED

    version column from AuditMixin provides optimistic locking.
    Once CLOSED, all mutations return 403 (enforced in service layer).
    """
    __tablename__  = "mfg_production_orders"
    __table_args__ = (
        UniqueConstraint("company_id", "po_number", name="uq_mfg_po_number"),
        CheckConstraint(
            "status IN ('DRAFT','RELEASED','IN_PROGRESS','COMPLETED','CLOSED')",
            name="ck_mfg_po_status",
        ),
        CheckConstraint("planned_qty > 0", name="ck_mfg_po_planned_qty"),
    )

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    po_number       = Column(String(20),  nullable=False)
    product_id      = Column(BigInteger,  ForeignKey("mfg_products.id"), nullable=False)
    planned_qty     = Column(Numeric(18, 4), nullable=False, default=Decimal("1"))
    uom             = Column(String(10),  nullable=False, default="pcs")
    status          = Column(String(20),  nullable=False, default="DRAFT")
    scheduled_start = Column(DateTime(timezone=True), nullable=True)
    scheduled_end   = Column(DateTime(timezone=True), nullable=True)
    created_by      = Column(BigInteger,  nullable=True)   # user.id

    product      = relationship("MfgProduct",       foreign_keys=[product_id])
    raw_materials = relationship("MfgPORawMaterial", back_populates="production_order",
                                 cascade="all, delete-orphan",
                                 order_by="MfgPORawMaterial.sort_order")
    operations   = relationship("MfgPOOperation",   back_populates="production_order",
                                cascade="all, delete-orphan",
                                order_by="MfgPOOperation.op_sequence")
    transactions = relationship("MfgPOTransaction", back_populates="production_order",
                                order_by="MfgPOTransaction.tx_timestamp")

    def is_mutable(self) -> bool:
        """CLOSED orders must not be mutated."""
        return self.status != "CLOSED"

    def __repr__(self) -> str:
        return f"<MfgProductionOrder {self.po_number} status={self.status}>"


# ═══════════════════════════════════════════════════════════════════
# Raw Materials (frozen BOM snapshot per PO)
# ═══════════════════════════════════════════════════════════════════

class MfgPORawMaterial(AuditMixin, Base):
    """
    Frozen BOM snapshot for a Production Order.

    Copied from MfgBOMLine when PO is RELEASED.
    qty_issued and qty_consumed must never exceed qty_planned (DB CHECK).
    """
    __tablename__  = "mfg_po_raw_materials"
    __table_args__ = (
        UniqueConstraint("po_id", "material_id", name="uq_mfg_po_rm_material"),
        CheckConstraint("qty_issued   >= 0", name="ck_mfg_po_rm_issued_nn"),
        CheckConstraint("qty_consumed >= 0", name="ck_mfg_po_rm_consumed_nn"),
        CheckConstraint("qty_issued   <= qty_planned", name="ck_mfg_po_rm_issued_limit"),
        CheckConstraint("qty_consumed <= qty_planned", name="ck_mfg_po_rm_consumed_limit"),
        CheckConstraint("qty_planned  >  0", name="ck_mfg_po_rm_planned_pos"),
    )

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    po_id        = Column(BigInteger, ForeignKey("mfg_production_orders.id",
                           ondelete="CASCADE"), nullable=False)
    material_id  = Column(BigInteger, ForeignKey("mfg_products.id"), nullable=False)
    qty_planned  = Column(Numeric(18, 4), nullable=False)
    qty_issued   = Column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    qty_consumed = Column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    uom          = Column(String(10),     nullable=False, default="pcs")
    sort_order   = Column(Integer,        nullable=False, default=0)

    production_order = relationship("MfgProductionOrder", back_populates="raw_materials")
    material         = relationship("MfgProduct", foreign_keys=[material_id])

    @property
    def qty_remaining(self) -> Decimal:
        return self.qty_planned - self.qty_issued

    def can_issue(self, qty: Decimal) -> bool:
        return qty > 0 and (self.qty_issued + qty) <= self.qty_planned

    def can_consume(self, qty: Decimal) -> bool:
        return qty > 0 and (self.qty_consumed + qty) <= self.qty_planned


# ═══════════════════════════════════════════════════════════════════
# Operations (routing / process tracking)
# ═══════════════════════════════════════════════════════════════════

class MfgPOOperation(AuditMixin, Base):
    """
    Single routing step in a Production Order.

    Sequential enforcement rule:
        Operation N cannot be set IN_PROGRESS or COMPLETED
        until Operation N-1 is COMPLETED (or SKIPPED).
        This is enforced in ManufacturingOrgan.complete_operation(),
        NOT at DB level (to allow retroactive SKIPPED entries by supervisors).

    performed_by: nullable for PENDING; required by application logic when completing.
    """
    __tablename__  = "mfg_po_operations"
    __table_args__ = (
        UniqueConstraint("po_id", "op_sequence", name="uq_mfg_po_op_sequence"),
        CheckConstraint(
            "status IN ('PENDING','IN_PROGRESS','COMPLETED','SKIPPED')",
            name="ck_mfg_po_op_status",
        ),
        CheckConstraint("op_sequence >= 1", name="ck_mfg_po_op_seq_pos"),
    )

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    po_id           = Column(BigInteger, ForeignKey("mfg_production_orders.id",
                              ondelete="CASCADE"), nullable=False)
    op_sequence     = Column(Integer,     nullable=False)
    op_code         = Column(String(50),  nullable=False)
    op_name         = Column(String(255), nullable=False)
    workcenter_id   = Column(BigInteger,  ForeignKey("cells.id"), nullable=True)
    performed_by    = Column(String(100), nullable=True)    # operator name; nullable for PENDING
    started_at      = Column(DateTime(timezone=True), nullable=True)
    completed_at    = Column(DateTime(timezone=True), nullable=True)
    status          = Column(String(20),  nullable=False, default="PENDING")
    skip_reason     = Column(Text,        nullable=True)    # required when SKIPPED

    production_order = relationship("MfgProductionOrder", back_populates="operations")
    workcenter       = relationship("Cell", foreign_keys=[workcenter_id])

    def is_done(self) -> bool:
        return self.status in ("COMPLETED", "SKIPPED")

    def __repr__(self) -> str:
        return (f"<MfgPOOperation seq={self.op_sequence} "
                f"status={self.status} op={self.op_name!r}>")


# ═══════════════════════════════════════════════════════════════════
# Transaction ledger (Related Transactions tab — immutable)
# ═══════════════════════════════════════════════════════════════════

class MfgPOTransaction(Base):
    """
    Immutable audit ledger for all manufacturing inventory movements.

    tx_type values:
        RM_ISSUE    — raw material issued from warehouse to WIP
        RM_CONSUME  — raw material consumed in an operation (back-flush)
        FG_RECEIPT  — finished good received into stock on PO completion
        WIP_MOVE    — work-in-progress movement between work centers

    INSERT-only — no UPDATE or DELETE ever issued on this table.
    Rows are archived to cold storage after 12 months (Celery task).
    """
    __tablename__  = "mfg_po_transactions"
    __table_args__ = (
        CheckConstraint(
            "tx_type IN ('RM_ISSUE','RM_CONSUME','FG_RECEIPT','WIP_MOVE')",
            name="ck_mfg_tx_type",
        ),
        CheckConstraint("qty > 0", name="ck_mfg_tx_qty_pos"),
    )

    id             = Column(BigInteger, primary_key=True, autoincrement=True)
    po_id          = Column(BigInteger, ForeignKey("mfg_production_orders.id"),
                            nullable=False)
    tx_type        = Column(String(20),   nullable=False)
    reference_id   = Column(BigInteger,   nullable=True)   # rm_line or op_id
    qty            = Column(Numeric(18, 4), nullable=False)
    uom            = Column(String(10),   nullable=False)
    tx_timestamp   = Column(DateTime(timezone=True), nullable=False,
                            default=lambda: datetime.now(UTC))
    posted_by      = Column(String(100),  nullable=False)  # user display name
    notes          = Column(Text,         nullable=True)

    production_order = relationship("MfgProductionOrder", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<MfgPOTransaction {self.tx_type} qty={self.qty} po={self.po_id}>"


# ═══════════════════════════════════════════════════════════════════
# Inventory — Warehouse / Location / Stock Movement
# ═══════════════════════════════════════════════════════════════════

class MfgWarehouse(CompanyTenantMixin, AuditMixin, Base):
    """Physical warehouse location."""
    __tablename__  = "mfg_warehouses"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_mfg_warehouse_code"),
    )

    id          = Column(BigInteger, primary_key=True, autoincrement=True)
    code        = Column(String(20),  nullable=False)
    name        = Column(String(100), nullable=False)
    is_active   = Column(Boolean,     nullable=False, default=True)

    locations = relationship("MfgLocation", back_populates="warehouse",
                             cascade="all, delete-orphan")


class MfgLocation(AuditMixin, Base):
    """Bin / shelf location within a warehouse."""
    __tablename__  = "mfg_locations"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_mfg_location_code"),
    )

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    warehouse_id = Column(BigInteger, ForeignKey("mfg_warehouses.id",
                           ondelete="CASCADE"), nullable=False)
    code         = Column(String(30),  nullable=False)
    name         = Column(String(100), nullable=False)
    is_active    = Column(Boolean,     nullable=False, default=True)

    warehouse = relationship("MfgWarehouse", back_populates="locations")


class MfgStockMovement(Base):
    """
    Immutable inventory ledger — mirrors MfgPOTransaction pattern.
    Each RM issue / FG receipt also writes here for running-balance queries.
    """
    __tablename__  = "mfg_stock_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('IN','OUT','ADJUSTMENT')",
            name="ck_mfg_stock_type",
        ),
    )

    id              = Column(BigInteger, primary_key=True, autoincrement=True)
    product_id      = Column(BigInteger, ForeignKey("mfg_products.id"), nullable=False)
    location_id     = Column(BigInteger, ForeignKey("mfg_locations.id"), nullable=True)
    movement_type   = Column(String(20),    nullable=False)
    qty             = Column(Numeric(18, 4), nullable=False)
    uom             = Column(String(10),    nullable=False)
    reference_type  = Column(String(30),    nullable=True)   # 'MfgProductionOrder'
    reference_id    = Column(BigInteger,    nullable=True)
    running_balance = Column(Numeric(18, 4), nullable=True)
    movement_at     = Column(DateTime(timezone=True), nullable=False,
                             default=lambda: datetime.now(UTC))
    posted_by       = Column(String(100),   nullable=False)

    product  = relationship("MfgProduct",  foreign_keys=[product_id])
    location = relationship("MfgLocation", foreign_keys=[location_id])
