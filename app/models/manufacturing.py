from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# ── Bio Entity Models ────────────────────────────────────────────

class Bioreactor(Base):
    __tablename__ = "bioreactors"
    id = Column(Integer, primary_key=True)
    reactor_code = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    reactor_type = Column(String(50), default="stirred_tank")
    working_volume_l = Column(Float, nullable=False, default=0)
    max_volume_l = Column(Float, nullable=True)
    temperature_range = Column(String(100), nullable=True)
    ph_range = Column(String(50), nullable=True)
    agitation_rpm = Column(Integer, nullable=True)
    aeration_rate_vvm = Column(Float, nullable=True)
    status = Column(String(50), default="available")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    batches = relationship("Batch", back_populates="bioreactor", foreign_keys="Batch.bioreactor_id")


class CellLine(Base):
    __tablename__ = "cell_lines"
    id = Column(Integer, primary_key=True)
    cell_code = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    organism = Column(String(100), nullable=True)
    cell_type = Column(String(100), default="CHO")
    doubling_time_hr = Column(Float, nullable=True)
    max_density_cells_per_ml = Column(Float, nullable=True)
    viability_threshold = Column(Float, default=80.0)
    atp_maintenance_cost = Column(Float, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    batches = relationship("Batch", back_populates="cell_line", foreign_keys="Batch.cell_line_id")


class GeneConstruct(Base):
    __tablename__ = "gene_constructs"
    id = Column(Integer, primary_key=True)
    construct_code = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    plasmid_size_kb = Column(Float, nullable=True)
    copy_number = Column(Integer, default=50)
    induction_method = Column(String(100), default="iptg")
    promoter = Column(String(100), nullable=True)
    resistance_marker = Column(String(50), nullable=True)
    construction_cost_egp = Column(Float, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    batches = relationship("Batch", back_populates="gene_construct", foreign_keys="Batch.gene_construct_id")


class RawMaterial(Base):
    __tablename__ = "raw_materials"
    id = Column(Integer, primary_key=True)
    material_code = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    material_type = Column(String(50), default="substrate")
    unit_cost_egp = Column(Float, default=0)
    atp_per_mol = Column(Float, default=0)
    density_g_per_l = Column(Float, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class BatchStatus(str, enum.Enum):
    DRAFT = "draft"
    RELEASED = "released"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[BatchStatus, set[BatchStatus]] = {
    BatchStatus.DRAFT: {BatchStatus.RELEASED, BatchStatus.CANCELLED},
    BatchStatus.RELEASED: {BatchStatus.IN_PROGRESS, BatchStatus.CANCELLED},
    BatchStatus.IN_PROGRESS: {BatchStatus.COMPLETED, BatchStatus.CANCELLED},
    BatchStatus.COMPLETED: {BatchStatus.ARCHIVED},
    BatchStatus.ARCHIVED: set(),
    BatchStatus.CANCELLED: set(),
}


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True)
    batch_number = Column(String(50), nullable=False, unique=True)
    status = Column(Enum(BatchStatus), default=BatchStatus.DRAFT, nullable=False)
    phase = Column(String(50), default="lag")

    bioreactor_id = Column(Integer, ForeignKey("bioreactors.id"), nullable=True)
    cell_line_id = Column(Integer, ForeignKey("cell_lines.id"), nullable=True)
    gene_construct_id = Column(Integer, ForeignKey("gene_constructs.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("raw_materials.id"), nullable=True)

    bioreactor = relationship("Bioreactor", back_populates="batches", foreign_keys=[bioreactor_id])
    cell_line = relationship("CellLine", back_populates="batches", foreign_keys=[cell_line_id])
    gene_construct = relationship("GeneConstruct", back_populates="batches", foreign_keys=[gene_construct_id])

    volume_l = Column(Float, default=0.0)
    inoculum_density = Column(Float, nullable=True)
    target_biomass_gl = Column(Float, nullable=True)
    actual_biomass_gl = Column(Float, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=True)
    harvest_time = Column(DateTime(timezone=True), nullable=True)
    total_cost_egp = Column(Float, default=0.0)
    yield_achieved = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)

    steps = relationship("BatchStep", back_populates="batch", order_by="BatchStep.sequence")
    status_history = relationship("BatchStatusHistory", back_populates="batch", order_by="BatchStatusHistory.changed_at")


class BatchStep(Base):
    __tablename__ = "batch_steps"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    operation = Column(String(100), nullable=False)
    status = Column(String(50), default="pending")
    planned_duration_hr = Column(Float, nullable=True)
    actual_duration_hr = Column(Float, nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    batch = relationship("Batch", back_populates="steps")


class BatchStatusHistory(Base):
    __tablename__ = "batch_status_history"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("batches.id"), nullable=False)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reason = Column(Text, nullable=True)

    batch = relationship("Batch", back_populates="status_history")
