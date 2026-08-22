from datetime import datetime, date
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Boolean, Date, Text, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.database import Base
from app.models.base import BaseMixin, BilingualMixin, AuditableMixin


class DepreciationMethod(str, enum.Enum):
    SL = "straight_line"
    DB = "declining_balance"
    SYD = "sum_of_years_digits"


class AssetStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    FULLY_DEPRECIATED = "fully_depreciated"
    DISPOSED = "disposed"
    IMPAIRED = "impaired"


class DisposalType(str, enum.Enum):
    SALE = "sale"
    SCRAP = "scrap"
    DONATION = "donation"
    THEFT = "theft"


class FACategory(Base, BaseMixin, BilingualMixin):
    __tablename__ = "fa_categories"
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    default_dep_method: Mapped[DepreciationMethod] = mapped_column(Enum(DepreciationMethod), default=DepreciationMethod.SL)
    default_useful_life: Mapped[int] = mapped_column(Integer, default=60)
    default_salvage_pct: Mapped[float] = mapped_column(Float, default=0.0)
    gl_asset_account_id: Mapped[int] = mapped_column(Integer, nullable=True)
    gl_dep_expense_account_id: Mapped[int] = mapped_column(Integer, nullable=True)
    gl_acc_dep_account_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    assets = relationship("FAAsset", back_populates="category")


class FAAsset(Base, BaseMixin, BilingualMixin):
    __tablename__ = "fa_assets"
    asset_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("fa_categories.id"), nullable=False)
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False)
    capitalization_date: Mapped[date] = mapped_column(Date, nullable=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    salvage_value: Mapped[float] = mapped_column(Float, default=0.0)
    useful_life_months: Mapped[int] = mapped_column(Integer, default=60)
    dep_method: Mapped[DepreciationMethod] = mapped_column(Enum(DepreciationMethod), default=DepreciationMethod.SL)
    accumulated_dep: Mapped[float] = mapped_column(Float, default=0.0)
    net_book_value: Mapped[float] = mapped_column(Float, default=0.0)
    last_depreciation_date: Mapped[date] = mapped_column(Date, nullable=True)
    status: Mapped[AssetStatus] = mapped_column(Enum(AssetStatus), default=AssetStatus.DRAFT)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str] = mapped_column(String(100), nullable=True)
    gl_asset_account_id: Mapped[int] = mapped_column(Integer, nullable=True)
    gl_dep_expense_account_id: Mapped[int] = mapped_column(Integer, nullable=True)
    gl_acc_dep_account_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    category = relationship("FACategory", back_populates="assets")
    depreciation_entries = relationship("FADepreciationEntry", back_populates="asset", cascade="all, delete-orphan")


class FADepreciationEntry(Base, BaseMixin):
    __tablename__ = "fa_depreciation_entries"
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("fa_assets.id"), nullable=False)
    period_id: Mapped[int] = mapped_column(Integer, nullable=False)
    depreciation_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    running_total: Mapped[float] = mapped_column(Float, default=0.0)
    net_book_value_after: Mapped[float] = mapped_column(Float, default=0.0)
    journal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    asset = relationship("FAAsset", back_populates="depreciation_entries")


class FADisposal(Base, BaseMixin, AuditableMixin):
    __tablename__ = "fa_disposals"
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("fa_assets.id"), nullable=False)
    disposal_date: Mapped[date] = mapped_column(Date, nullable=False)
    disposal_type: Mapped[DisposalType] = mapped_column(Enum(DisposalType), default=DisposalType.SALE)
    proceeds: Mapped[float] = mapped_column(Float, default=0.0)
    cost_removed: Mapped[float] = mapped_column(Float, default=0.0)
    acc_dep_removed: Mapped[float] = mapped_column(Float, default=0.0)
    gain_loss: Mapped[float] = mapped_column(Float, default=0.0)
    journal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    asset = relationship("FAAsset")


class FARevaluation(Base, BaseMixin, AuditableMixin):
    __tablename__ = "fa_revaluations"
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("fa_assets.id"), nullable=False)
    revaluation_date: Mapped[date] = mapped_column(Date, nullable=False)
    old_value: Mapped[float] = mapped_column(Float, default=0.0)
    new_value: Mapped[float] = mapped_column(Float, default=0.0)
    change_amount: Mapped[float] = mapped_column(Float, default=0.0)
    journal_id: Mapped[int] = mapped_column(Integer, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    asset = relationship("FAAsset")
