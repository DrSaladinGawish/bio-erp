from datetime import date, datetime, timedelta
from math import floor
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.organs.far_fa_organ.models import (
    FACategory, FAAsset, FADepreciationEntry, FADisposal, FARevaluation,
    DepreciationMethod, AssetStatus, DisposalType
)
from app.organs.far_fa_organ import schemas
from app.organs.far_gl_organ.service import JournalService as GLJournalService
from app.organs.far_gl_organ.schemas import JournalCreate as GLJournalCreate, JournalLineCreate as GLJournalLineCreate


class FACategoryService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: schemas.CategoryCreate) -> FACategory:
        cat = FACategory(
            code=data.code, name_en=data.name_en, name_ar=data.name_ar,
            default_dep_method=DepreciationMethod(data.default_dep_method),
            default_useful_life=data.default_useful_life,
            default_salvage_pct=data.default_salvage_pct,
            gl_asset_account_id=data.gl_asset_account_id,
            gl_dep_expense_account_id=data.gl_dep_expense_account_id,
            gl_acc_dep_account_id=data.gl_acc_dep_account_id,
            notes=data.notes,
        )
        self.db.add(cat); self.db.flush()
        return cat

    def get_all(self) -> List[FACategory]:
        return self.db.query(FACategory).all()

    def get_by_id(self, cat_id: int) -> Optional[FACategory]:
        return self.db.query(FACategory).filter(FACategory.id == cat_id).first()

    def update(self, cat_id: int, data: schemas.CategoryCreate) -> Optional[FACategory]:
        cat = self.get_by_id(cat_id)
        if not cat:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            if k == "default_dep_method":
                setattr(cat, k, DepreciationMethod(v))
            else:
                setattr(cat, k, v)
        self.db.flush()
        return cat


class DepreciationEngine:
    MONTHS_PER_YEAR = 12

    @classmethod
    def monthly_depreciation_sl(cls, cost: float, salvage: float, useful_life_months: int, months_elapsed: int = 0) -> float:
        if useful_life_months <= 0:
            return 0.0
        annual = (cost - salvage) / (useful_life_months / cls.MONTHS_PER_YEAR)
        return round(annual / cls.MONTHS_PER_YEAR, 2)

    @classmethod
    def monthly_depreciation_db(cls, cost: float, salvage: float, useful_life_months: int, months_elapsed: int = 0) -> float:
        if useful_life_months <= 0:
            return 0.0
        rate = 2.0 / (useful_life_months / cls.MONTHS_PER_YEAR)
        remaining_cost = cost - 0.0  # simplified; caller should provide accumulated
        return round(remaining_cost * rate / cls.MONTHS_PER_YEAR, 2)

    @classmethod
    def monthly_depreciation_syd(cls, cost: float, salvage: float, useful_life_months: int, months_elapsed: int = 0) -> float:
        if useful_life_months <= 0:
            return 0.0
        n = useful_life_months / cls.MONTHS_PER_YEAR
        syd_total = n * (n + 1) / 2
        remaining_years = n - (months_elapsed / cls.MONTHS_PER_YEAR)
        if remaining_years <= 0:
            return 0.0
        annual = ((cost - salvage) * remaining_years / syd_total)
        return round(annual / cls.MONTHS_PER_YEAR, 2)

    @classmethod
    def calculate(cls, method: DepreciationMethod, cost: float, salvage: float,
                  useful_life_months: int, accumulated_dep: float, months_elapsed: int = 0) -> float:
        if method == DepreciationMethod.SL:
            return cls.monthly_depreciation_sl(cost, salvage, useful_life_months, months_elapsed)
        elif method == DepreciationMethod.DB:
            return cls.monthly_depreciation_db(cost - accumulated_dep, salvage, useful_life_months, months_elapsed)
        elif method == DepreciationMethod.SYD:
            return cls.monthly_depreciation_syd(cost, salvage, useful_life_months, months_elapsed)
        return 0.0


class FAAssetService:
    def __init__(self, db: Session):
        self.db = db
        self.journal_service = GLJournalService(db)

    def create(self, data: schemas.AssetCreate) -> FAAsset:
        asset = FAAsset(
            asset_number=data.asset_number, category_id=data.category_id,
            name_en=data.name_en, name_ar=data.name_ar,
            purchase_date=data.purchase_date,
            capitalization_date=data.capitalization_date or data.purchase_date,
            cost=data.cost, salvage_value=data.salvage_value,
            useful_life_months=data.useful_life_months,
            dep_method=DepreciationMethod(data.dep_method),
            accumulated_dep=0.0, net_book_value=data.cost,
            status=AssetStatus.DRAFT,
            location=data.location, serial_number=data.serial_number,
            gl_asset_account_id=data.gl_asset_account_id,
            gl_dep_expense_account_id=data.gl_dep_expense_account_id,
            gl_acc_dep_account_id=data.gl_acc_dep_account_id,
            notes=data.notes,
        )
        self.db.add(asset); self.db.flush()
        return asset

    def activate(self, asset_id: int) -> Optional[FAAsset]:
        asset = self.get_by_id(asset_id)
        if not asset:
            return None
        asset.status = AssetStatus.ACTIVE
        asset.net_book_value = asset.cost
        self.db.flush()
        return asset

    def get_all(self) -> List[FAAsset]:
        return self.db.query(FAAsset).all()

    def get_by_id(self, asset_id: int) -> Optional[FAAsset]:
        return self.db.query(FAAsset).filter(FAAsset.id == asset_id).first()

    def update(self, asset_id: int, data: schemas.AssetUpdate) -> Optional[FAAsset]:
        asset = self.get_by_id(asset_id)
        if not asset:
            return None
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(asset, k, v)
        asset.net_book_value = asset.cost - asset.accumulated_dep
        self.db.flush()
        return asset

    def _get_or_default_account(self, asset: FAAsset, field: str, cat_field: str) -> int:
        val = getattr(asset, field)
        if val:
            return val
        cat = self.db.query(FACategory).filter(FACategory.id == asset.category_id).first()
        if cat and getattr(cat, cat_field):
            return getattr(cat, cat_field)
        return 0

    def _post_depreciation_journal(self, asset: FAAsset, amount: float, entry_date: date, period_id: int) -> Optional[int]:
        gl_asset = self._get_or_default_account(asset, "gl_asset_account_id", "gl_asset_account_id")
        gl_dep_exp = self._get_or_default_account(asset, "gl_dep_expense_account_id", "gl_dep_expense_account_id")
        gl_acc_dep = self._get_or_default_account(asset, "gl_acc_dep_account_id", "gl_acc_dep_account_id")
        if not gl_dep_exp or not gl_acc_dep:
            return None
        lines = [
            GLJournalLineCreate(account_id=gl_dep_exp, debit_amount=amount, credit_amount=0.0,
                line_description=f"Depreciation expense: {asset.asset_number}"),
            GLJournalLineCreate(account_id=gl_acc_dep, debit_amount=0.0, credit_amount=amount,
                line_description=f"Accumulated depreciation: {asset.asset_number}"),
        ]
        journal = self.journal_service.create(GLJournalCreate(
            period_id=period_id, journal_date=entry_date,
            description=f"Depreciation for {asset.name_en} ({entry_date.isoformat()})",
            source="fa", reference_type="fa_depreciation", lines=lines,
        ))
        posted = self.journal_service.post(journal.id)
        return posted.id

    def run_depreciation(self, asset_id: int, period_id: int, run_date: date) -> Optional[List[FADepreciationEntry]]:
        asset = self.get_by_id(asset_id)
        if not asset or asset.status not in (AssetStatus.ACTIVE,):
            return None
        if asset.last_depreciation_date and run_date <= asset.last_depreciation_date:
            return None
        if asset.net_book_value <= asset.salvage_value:
            return None

        months_from_last = 1
        if asset.last_depreciation_date:
            months_from_last = max(1, (run_date.year - asset.last_depreciation_date.year) * 12
                                   + run_date.month - asset.last_depreciation_date.month)

        months_elapsed = months_from_last
        amount = DepreciationEngine.calculate(
            asset.dep_method, asset.cost, asset.salvage_value,
            asset.useful_life_months, asset.accumulated_dep, months_elapsed
        )
        if amount <= 0:
            return None

        max_dep = max(0, asset.cost - asset.salvage_value - asset.accumulated_dep)
        if amount > max_dep:
            amount = max_dep
        if amount <= 0:
            return None

        new_total = asset.accumulated_dep + amount
        new_nbv = max(0, asset.cost - new_total)

        journal_id = self._post_depreciation_journal(asset, amount, run_date, period_id)

        entry = FADepreciationEntry(
            asset_id=asset_id, period_id=period_id,
            depreciation_date=run_date, amount=amount,
            running_total=new_total, net_book_value_after=new_nbv,
            journal_id=journal_id,
        )
        self.db.add(entry)
        asset.accumulated_dep = new_total
        asset.net_book_value = new_nbv
        asset.last_depreciation_date = run_date
        if new_total >= (asset.cost - asset.salvage_value):
            asset.status = AssetStatus.FULLY_DEPRECIATED
        self.db.flush()
        return [entry]

    def run_all_depreciation(self, period_id: int, run_date: date) -> List[FADepreciationEntry]:
        assets = self.db.query(FAAsset).filter(FAAsset.status == AssetStatus.ACTIVE).all()
        results = []
        for asset in assets:
            entries = self.run_depreciation(asset.id, period_id, run_date)
            if entries:
                results.extend(entries)
        return results

    def get_depreciation_entries(self, asset_id: int) -> List[FADepreciationEntry]:
        return self.db.query(FADepreciationEntry).filter(
            FADepreciationEntry.asset_id == asset_id
        ).order_by(FADepreciationEntry.depreciation_date).all()

    def dispose(self, asset_id: int, data: schemas.DisposalCreate) -> Optional[FADisposal]:
        asset = self.get_by_id(asset_id)
        if not asset or asset.status == AssetStatus.DISPOSED:
            return None

        cost_removed = asset.cost
        acc_dep_removed = asset.accumulated_dep
        nbv = cost_removed - acc_dep_removed
        gain_loss = data.proceeds - nbv

        gl_asset = self._get_or_default_account(asset, "gl_asset_account_id", "gl_asset_account_id")
        gl_acc_dep = self._get_or_default_account(asset, "gl_acc_dep_account_id", "gl_acc_dep_account_id")
        gain_loss_acct = 0
        if gain_loss > 0 and gl_asset:
            gain_loss_acct = gl_asset + 100
        elif gain_loss < 0 and gl_asset:
            gain_loss_acct = gl_asset + 200

        gl_lines = []
        if gl_acc_dep:
            gl_lines.append(GLJournalLineCreate(account_id=gl_acc_dep, debit_amount=acc_dep_removed, credit_amount=0.0,
                line_description=f"Acc dep removed: {asset.asset_number}"))
        if gl_asset:
            gl_lines.append(GLJournalLineCreate(account_id=gl_asset, debit_amount=0.0, credit_amount=cost_removed,
                line_description=f"Asset cost removed: {asset.asset_number}"))
        if gain_loss != 0 and gain_loss_acct:
            if gain_loss > 0:
                gl_lines.append(GLJournalLineCreate(account_id=gain_loss_acct, debit_amount=0.0, credit_amount=gain_loss,
                    line_description=f"Gain on disposal: {asset.asset_number}"))
            else:
                gl_lines.append(GLJournalLineCreate(account_id=gain_loss_acct, debit_amount=abs(gain_loss), credit_amount=0.0,
                    line_description=f"Loss on disposal: {asset.asset_number}"))

        journal_id = None
        if gl_lines:
            journal = self.journal_service.create(GLJournalCreate(
                period_id=1, journal_date=data.disposal_date,
                description=f"Disposal of {asset.name_en} ({data.disposal_type})",
                source="fa", reference_type="fa_disposal", lines=gl_lines,
            ))
            posted = self.journal_service.post(journal.id)
            journal_id = posted.id

        disposal = FADisposal(
            asset_id=asset_id, disposal_date=data.disposal_date,
            disposal_type=DisposalType(data.disposal_type),
            proceeds=data.proceeds, cost_removed=cost_removed,
            acc_dep_removed=acc_dep_removed, gain_loss=gain_loss,
            journal_id=journal_id, notes=data.notes,
        )
        self.db.add(disposal)
        asset.status = AssetStatus.DISPOSED
        asset.net_book_value = 0
        self.db.flush()
        return disposal

    def revalue(self, asset_id: int, data: schemas.RevaluationCreate) -> Optional[FARevaluation]:
        asset = self.get_by_id(asset_id)
        if not asset or asset.status == AssetStatus.DISPOSED:
            return None

        old_value = asset.net_book_value
        new_value = data.new_value
        change_amount = new_value - old_value

        if change_amount == 0:
            return None

        gl_asset = self._get_or_default_account(asset, "gl_asset_account_id", "gl_asset_account_id")
        reval_reserve_acct = (gl_asset + 300) if gl_asset else 0

        gl_lines = []
        if gl_asset and reval_reserve_acct and change_amount > 0:
            gl_lines.append(GLJournalLineCreate(account_id=gl_asset, debit_amount=change_amount, credit_amount=0.0,
                line_description=f"Asset increase: {asset.asset_number}"))
            gl_lines.append(GLJournalLineCreate(account_id=reval_reserve_acct, debit_amount=0.0, credit_amount=change_amount,
                line_description=f"Revaluation reserve: {asset.asset_number}"))
        elif gl_asset and reval_reserve_acct and change_amount < 0:
            gl_lines.append(GLJournalLineCreate(account_id=reval_reserve_acct, debit_amount=abs(change_amount), credit_amount=0.0,
                line_description=f"Revaluation decrease: {asset.asset_number}"))
            gl_lines.append(GLJournalLineCreate(account_id=gl_asset, debit_amount=0.0, credit_amount=abs(change_amount),
                line_description=f"Asset decrease: {asset.asset_number}"))

        journal_id = None
        if gl_lines:
            journal = self.journal_service.create(GLJournalCreate(
                period_id=1, journal_date=data.revaluation_date,
                description=f"Revaluation of {asset.name_en}",
                source="fa", reference_type="fa_revaluation", lines=gl_lines,
            ))
            posted = self.journal_service.post(journal.id)
            journal_id = posted.id

        reval = FARevaluation(
            asset_id=asset_id, revaluation_date=data.revaluation_date,
            old_value=old_value, new_value=new_value,
            change_amount=change_amount, journal_id=journal_id,
            notes=data.notes,
        )
        self.db.add(reval)
        asset.cost = new_value
        asset.net_book_value = new_value
        if change_amount > 0:
            asset.status = AssetStatus.ACTIVE
        self.db.flush()
        return reval


class FADisposalService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_asset(self, asset_id: int) -> List[FADisposal]:
        return self.db.query(FADisposal).filter(FADisposal.asset_id == asset_id).all()


class FARevaluationService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_asset(self, asset_id: int) -> List[FARevaluation]:
        return self.db.query(FARevaluation).filter(FARevaluation.asset_id == asset_id).all()


class FAHealthService:
    def __init__(self, db: Session):
        self.db = db

    def health(self) -> schemas.HealthResponse:
        cat_count = self.db.query(func.count(FACategory.id)).scalar() or 0
        asset_count = self.db.query(func.count(FAAsset.id)).scalar() or 0
        return schemas.HealthResponse(
            status="healthy", module="far-fa", version="1.0.0",
            categories=cat_count, assets=asset_count,
        )
