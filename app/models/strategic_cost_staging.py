from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, Boolean, ForeignKey, JSON, Numeric
from sqlalchemy.sql import func
from app.database import Base

class SCMStagingCategory(Base):
    __tablename__ = "scm_staging_categories"
    id = Column(Integer, primary_key=True, index=True)
    staging_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    code = Column(String(20), nullable=False)
    description = Column(Text)
    parent_id = Column(Integer, nullable=True)
    status = Column(String(20), default="pending")
    created_by = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deployed_at = Column(DateTime, nullable=True)
    deployed_by = Column(Integer, nullable=True)

class SCMStagingCostDriver(Base):
    __tablename__ = "scm_staging_cost_drivers"
    id = Column(Integer, primary_key=True, index=True)
    staging_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    category_id = Column(Integer, nullable=False)
    measurement_unit = Column(String(50))
    cost_per_unit = Column(Numeric(15, 2), default=0)
    status = Column(String(20), default="pending")
    created_by = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now())

class SCMStagingActivityCost(Base):
    __tablename__ = "scm_staging_activity_costs"
    id = Column(Integer, primary_key=True, index=True)
    staging_id = Column(String(50), unique=True, nullable=False)
    activity_name = Column(String(100), nullable=False)
    cost_driver_id = Column(Integer, nullable=False)
    actual_quantity = Column(Numeric(15, 2), default=0)
    actual_cost = Column(Numeric(15, 2), default=0)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    job_id = Column(String(50), nullable=True)
    notes = Column(Text)
    status = Column(String(20), default="pending")
    created_by = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

class SCMStagingSustainability(Base):
    __tablename__ = "scm_staging_sustainability"
    id = Column(Integer, primary_key=True, index=True)
    staging_id = Column(String(50), unique=True, nullable=False)
    environmental_cost = Column(Numeric(15, 2), default=0)
    social_cost = Column(Numeric(15, 2), default=0)
    governance_cost = Column(Numeric(15, 2), default=0)
    carbon_footprint_kg = Column(Numeric(15, 2), default=0)
    implied_carbon_cost = Column(Numeric(15, 2), default=0)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    job_id = Column(String(50), nullable=True)
    status = Column(String(20), default="pending")
    created_by = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

class SCMStagingBankTransaction(Base):
    __tablename__ = "scm_staging_bank_transactions"
    id = Column(Integer, primary_key=True, index=True)
    staging_id = Column(String(50), unique=True, nullable=False)
    import_id = Column(String(50), nullable=False)
    bank_account_id = Column(String(50), nullable=False)
    transaction_date = Column(Date, nullable=False)
    description = Column(Text)
    amount = Column(Numeric(15, 2), default=0)
    currency = Column(String(3), default="USD")
    reference_no = Column(String(100))
    matched = Column(Boolean, default=False)
    matched_transaction_id = Column(String(50), nullable=True)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default=func.now())

class SCMAuditLog(Base):
    __tablename__ = "scm_audit_log"
    id = Column(Integer, primary_key=True, index=True)
    staging_id = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    table_name = Column(String(50), nullable=False)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    performed_by = Column(Integer, default=1)
    performed_at = Column(DateTime, server_default=func.now())
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

class SCMDeploymentQueue(Base):
    __tablename__ = "scm_deployment_queue"
    id = Column(Integer, primary_key=True, index=True)
    staging_id = Column(String(50), unique=True, nullable=False)
    table_name = Column(String(50), nullable=False)
    deployment_batch = Column(String(50), nullable=True)
    status = Column(String(20), default="queued")
    scheduled_at = Column(DateTime, nullable=True)
    deployed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
