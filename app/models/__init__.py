from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name_en = Column(String, nullable=True)
    full_name_ar = Column(String, nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    is_superuser = Column(Boolean, nullable=False, default=False)
    last_login = Column(DateTime(timezone=False), nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    is_system = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    module = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    address_en = Column(String, nullable=True)
    address_ar = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    tax_authority = Column(String, nullable=True)
    vat_rate = Column(Float, nullable=False, default=0.0)
    country = Column(String, nullable=False)
    currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)
    is_hq = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class Currency(Base):
    __tablename__ = "currencies"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    symbol = Column(String, nullable=False)
    is_base = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    mid_rate = Column(Float, nullable=False, default=0.0)
    buy_rate = Column(Float, nullable=False, default=0.0)
    sell_rate = Column(Float, nullable=False, default=0.0)
    last_sync_at = Column(DateTime(timezone=False), nullable=True)
    decimal_places = Column(Integer, nullable=False, default=2)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)


class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id = Column(Integer, primary_key=True)
    from_currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)
    to_currency_id = Column(Integer, ForeignKey("currencies.id"), nullable=False)
    rate = Column(Float, nullable=False)
    rate_date = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class COACategory(Base):
    __tablename__ = "coa_categories"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    report_type = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class COAAccount(Base):
    __tablename__ = "coa_accounts"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    category_id = Column(Integer, ForeignKey("coa_categories.id"), nullable=False)
    account_type = Column(String, nullable=True)
    is_control_account = Column(Boolean, nullable=False, default=False)
    parent_id = Column(Integer, ForeignKey("coa_accounts.id"), nullable=True)
    opening_balance = Column(Float, nullable=False, default=0.0)
    opening_balance_date = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class TransactionType(Base):
    __tablename__ = "transaction_types"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=False, unique=True)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    sign_effect = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String, nullable=True)
    action = Column(String, nullable=False)
    target_type = Column(String, nullable=False)
    target_id = Column(Integer, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    description = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=True)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)
    commercial_registration = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone1 = Column(String, nullable=True)
    phone2 = Column(String, nullable=True)
    address_en = Column(String, nullable=True)
    address_ar = Column(String, nullable=True)
    credit_limit = Column(Float, nullable=False, default=0.0)
    balance = Column(Float, nullable=False, default=0.0)
    acc_key = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    code = Column(String, nullable=True)
    name_en = Column(String, nullable=False)
    name_ar = Column(String, nullable=True)
    tax_id = Column(String, nullable=True)
    commercial_registration = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone1 = Column(String, nullable=True)
    phone2 = Column(String, nullable=True)
    address_en = Column(String, nullable=True)
    address_ar = Column(String, nullable=True)
    service_category = Column(String, nullable=True)
    rating = Column(Float, nullable=False, default=0.0)
    acc_key = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    created_at = Column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
