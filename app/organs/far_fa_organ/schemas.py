from datetime import date, datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    code: str; name_en: str; name_ar: Optional[str] = None
    default_dep_method: str = "straight_line"; default_useful_life: int = 60
    default_salvage_pct: float = 0.0
    gl_asset_account_id: Optional[int] = None
    gl_dep_expense_account_id: Optional[int] = None
    gl_acc_dep_account_id: Optional[int] = None
    notes: Optional[str] = None


class CategoryResponse(BaseModel):
    id: int; code: str; name_en: str; name_ar: Optional[str] = None
    default_dep_method: str; default_useful_life: int; default_salvage_pct: float
    created_at: datetime


class AssetCreate(BaseModel):
    asset_number: str; category_id: int; name_en: str; name_ar: Optional[str] = None
    purchase_date: date; capitalization_date: Optional[date] = None
    cost: float = Field(..., gt=0); salvage_value: float = 0.0
    useful_life_months: int = 60; dep_method: str = "straight_line"
    location: Optional[str] = None; serial_number: Optional[str] = None
    gl_asset_account_id: Optional[int] = None
    gl_dep_expense_account_id: Optional[int] = None
    gl_acc_dep_account_id: Optional[int] = None
    notes: Optional[str] = None


class AssetUpdate(BaseModel):
    name_en: Optional[str] = None; location: Optional[str] = None
    salvage_value: Optional[float] = None; useful_life_months: Optional[int] = None
    notes: Optional[str] = None


class AssetResponse(BaseModel):
    id: int; asset_number: str; category_id: int; name_en: str; name_ar: Optional[str] = None
    purchase_date: date; cost: float; salvage_value: float
    useful_life_months: int; dep_method: str; accumulated_dep: float
    net_book_value: float; status: str; location: Optional[str] = None
    created_at: datetime


class DepreciationRun(BaseModel):
    period_id: int; run_date: date; notes: Optional[str] = None


class DepreciationEntryResponse(BaseModel):
    id: int; asset_id: int; period_id: int; depreciation_date: date
    amount: float; running_total: float; net_book_value_after: float
    journal_id: Optional[int] = None


class DisposalCreate(BaseModel):
    disposal_date: date; disposal_type: str = "sale"
    proceeds: float = 0.0; notes: Optional[str] = None


class DisposalResponse(BaseModel):
    id: int; asset_id: int; disposal_date: date; disposal_type: str
    proceeds: float; cost_removed: float; acc_dep_removed: float
    gain_loss: float; journal_id: Optional[int] = None


class RevaluationCreate(BaseModel):
    revaluation_date: date; new_value: float = Field(..., gt=0)
    notes: Optional[str] = None


class RevaluationResponse(BaseModel):
    id: int; asset_id: int; revaluation_date: date
    old_value: float; new_value: float; change_amount: float
    journal_id: Optional[int] = None


class MessageResponse(BaseModel):
    message: str; id: Optional[int] = None


class HealthResponse(BaseModel):
    status: str; module: str = "far-fa"; version: str = "1.0.0"
    categories: int = 0; assets: int = 0
