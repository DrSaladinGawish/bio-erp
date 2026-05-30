from datetime import datetime, date
from sqlalchemy import Integer, String, Float, DateTime, Date, Text, Boolean, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SCMStagingCategory(Base):
    __tablename__ = "scm_staging_categories"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("scm_staging_categories.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SCMStagingCostDriver(Base):
    __tablename__ = "scm_staging_cost_drivers"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("scm_staging_categories.id"), nullable=False)
    measurement_unit: Mapped[str] = mapped_column(String(100), nullable=False)
    cost_per_unit: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SCMStagingActivityCost(Base):
    __tablename__ = "scm_staging_activity_costs"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    activity_name: Mapped[str] = mapped_column(String(200), nullable=False)
    cost_driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("scm_staging_cost_drivers.id"), nullable=False)
    actual_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    actual_cost: Mapped[float] = mapped_column(Float, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    job_id: Mapped[str] = mapped_column(String(50), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SCMStagingSustainability(Base):
    __tablename__ = "scm_staging_sustainability"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    environmental_cost: Mapped[float] = mapped_column(Float, default=0.0)
    social_cost: Mapped[float] = mapped_column(Float, default=0.0)
    governance_cost: Mapped[float] = mapped_column(Float, default=0.0)
    carbon_footprint_kg: Mapped[float] = mapped_column(Float, default=0.0)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    job_id: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SCMStagingBankTransaction(Base):
    __tablename__ = "scm_staging_bank_transactions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_content: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    bank_account_id: Mapped[str] = mapped_column(String(100), nullable=False)
    import_date: Mapped[date] = mapped_column(Date, nullable=False)
    auto_match: Mapped[bool] = mapped_column(Boolean, default=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
