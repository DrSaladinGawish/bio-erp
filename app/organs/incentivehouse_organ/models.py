"""
SQLAlchemy models for IncentiveHouse ERP staging and audit tables.
All tables are staging-only — never writes to production ledger tables.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import declarative_base

IncentiveBase = declarative_base()


class IncentiveHouseAuditLog(IncentiveBase):
    __tablename__ = "incentivehouse_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), nullable=False, index=True)
    module = Column(String(20), nullable=False)
    source_file = Column(String(500))
    total_rows = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    warnings = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    staged = Column(Integer, default=0)
    dry_run = Column(Integer, default=1)
    summary = Column(Text)
    errors_json = Column(Text)
    started_at = Column(String(30))
    completed_at = Column(String(30), default=lambda: datetime.now().isoformat())


# ── Staging Table Models ──
# These mirror the Protocell's *__staging tables for SQLAlchemy ORM access.

class BnkStaging(IncentiveBase):
    __tablename__ = "bnk_staging"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), index=True)
    transaction_id = Column(String(50), index=True)
    transaction_date = Column(String(20))
    account_code = Column(String(20))
    description = Column(Text)
    debit_amount = Column(Float)
    credit_amount = Column(Float)
    currency = Column(String(3), default="EGP")
    exchange_rate = Column(Float, default=1.0)
    sub_led_code = Column(Integer)
    pnr_id = Column(Integer)
    client_id = Column(Integer)
    cost_center = Column(String(30))
    validation_status = Column(String(10), default="PASS")
    validation_errors = Column(Text)
    source_file = Column(String(200))
    source_row = Column(Integer)
    staged_at = Column(String(30), default=lambda: datetime.now().isoformat())


class SalStaging(IncentiveBase):
    __tablename__ = "sal_staging"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), index=True)
    transaction_id = Column(String(50), index=True)
    transaction_date = Column(String(20))
    account_code = Column(String(20))
    description = Column(Text)
    debit_amount = Column(Float)
    credit_amount = Column(Float)
    currency = Column(String(3), default="EGP")
    exchange_rate = Column(Float, default=1.0)
    sub_led_code = Column(Integer)
    pnr_id = Column(Integer)
    client_id = Column(Integer)
    cost_center = Column(String(30))
    validation_status = Column(String(10), default="PASS")
    validation_errors = Column(Text)
    source_file = Column(String(200))
    source_row = Column(Integer)
    staged_at = Column(String(30), default=lambda: datetime.now().isoformat())


class PurStaging(IncentiveBase):
    __tablename__ = "pur_staging"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), index=True)
    transaction_id = Column(String(50), index=True)
    transaction_date = Column(String(20))
    account_code = Column(String(20))
    description = Column(Text)
    debit_amount = Column(Float)
    credit_amount = Column(Float)
    currency = Column(String(3), default="EGP")
    exchange_rate = Column(Float, default=1.0)
    sub_led_code = Column(Integer)
    pnr_id = Column(Integer)
    client_id = Column(Integer)
    cost_center = Column(String(30))
    validation_status = Column(String(10), default="PASS")
    validation_errors = Column(Text)
    source_file = Column(String(200))
    source_row = Column(Integer)
    staged_at = Column(String(30), default=lambda: datetime.now().isoformat())


class EvnStaging(IncentiveBase):
    __tablename__ = "evn_staging"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), index=True)
    transaction_id = Column(String(50), index=True)
    transaction_date = Column(String(20))
    account_code = Column(String(20))
    description = Column(Text)
    debit_amount = Column(Float)
    credit_amount = Column(Float)
    currency = Column(String(3), default="EGP")
    exchange_rate = Column(Float, default=1.0)
    sub_led_code = Column(Integer)
    pnr_id = Column(Integer)
    client_id = Column(Integer)
    cost_center = Column(String(30))
    validation_status = Column(String(10), default="PASS")
    validation_errors = Column(Text)
    source_file = Column(String(200))
    source_row = Column(Integer)
    staged_at = Column(String(30), default=lambda: datetime.now().isoformat())


class EnvStaging(IncentiveBase):
    __tablename__ = "env_staging"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(50), index=True)
    transaction_id = Column(String(50), index=True)
    transaction_date = Column(String(20))
    account_code = Column(String(20))
    description = Column(Text)
    debit_amount = Column(Float)
    credit_amount = Column(Float)
    currency = Column(String(3), default="EGP")
    exchange_rate = Column(Float, default=1.0)
    sub_led_code = Column(Integer)
    pnr_id = Column(Integer)
    client_id = Column(Integer)
    cost_center = Column(String(30))
    validation_status = Column(String(10), default="PASS")
    validation_errors = Column(Text)
    source_file = Column(String(200))
    source_row = Column(Integer)
    staged_at = Column(String(30), default=lambda: datetime.now().isoformat())


class BNKTransaction(IncentiveBase):
    """Bank transaction record — used by the BNK router."""
    __tablename__ = "bnk_transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_code = Column(String(20), index=True)
    currency_code = Column(String(3), default="EGP")
    txn_date = Column(DateTime)
    txn_type = Column(String(50))
    description = Column(String(500))
    reference_no = Column(String(50), index=True)
    debit_amount = Column(Float, default=0.0)
    credit_amount = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)
    sub_ledger_code = Column(String(20))
    pnr_id = Column(Integer)
    counterparty = Column(String(200))
    is_reconciled = Column(Integer, default=0)
    is_flagged = Column(Integer, default=0)
    source = Column(String(50), default="excel_import")
    row_hash = Column(String(64), unique=True)
    imported_at = Column(DateTime)


# ── Module-to-model mapping ──
STAGING_MODELS = {
    "Bnk": BnkStaging,
    "Sal": SalStaging,
    "Pur": PurStaging,
    "Evn": EvnStaging,
    "Env": EnvStaging,
}

STAGING_TABLE_NAMES = {
    "Bnk": "bnk_staging",
    "Sal": "sal_staging",
    "Pur": "pur_staging",
    "Evn": "evn_staging",
    "Env": "env_staging",
}

PRODUCTION_TABLE_NAMES = {
    "Bnk": "bank_ledger",
    "Sal": "sales_ledger",
    "Pur": "purchase_ledger",
    "Evn": "event_ledger",
    "Env": "envelope_ledger",
}
