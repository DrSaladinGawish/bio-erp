"""
FAR-GL Service Layer — Core business logic for General Ledger.
8 service classes: Period, Account, Journal, TrialBalance,
AdjustingEntry, FinancialReport, YearEndClose, Health.
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session, joinedload

from app.organs.far_gl_organ.models import (
    GLPeriod, GLAccount, GLJournal, GLJournalLine,
    GLTrialBalance, GLAdjustingEntry, GLAdjustingEntryLine,
    GLYearEndClose,
    PeriodStatus, JournalStatus, AdjustingEntryStatus,
    AdjustingEntryType, NormalBalance, AccountType,
    YearEndStage,
)
from app.organs.far_gl_organ.coa_templates import (
    get_default_accounts, detect_template_from_text, merge_templates,
)
from app.organs.far_gl_organ import schemas

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _generate_journal_number(db: Session, fiscal_year: int) -> str:
    count = db.execute(
        select(func.count(GLJournal.id)).where(
            GLJournal.journal_number.like(f"JV-{fiscal_year}-%")
        )
    ).scalar() or 0
    return f"JV-{fiscal_year}-{count + 1:06d}"


def _generate_adjusting_number(db: Session, fiscal_year: int) -> str:
    count = db.execute(
        select(func.count(GLAdjustingEntry.id)).where(
            GLAdjustingEntry.entry_number.like(f"ADJ-{fiscal_year}-%")
        )
    ).scalar() or 0
    return f"ADJ-{fiscal_year}-{count + 1:04d}"


# ── Period Service ────────────────────────────────────────────────────

class PeriodService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: schemas.PeriodCreate) -> GLPeriod:
        existing = self.db.execute(
            select(GLPeriod).where(
                GLPeriod.fiscal_year == data.fiscal_year,
                GLPeriod.period_number == data.period_number,
            )
        ).scalar_one_or_none()
        if existing:
            raise ValueError(f"Period {data.fiscal_year}-{data.period_number} already exists")
        period = GLPeriod(**data.model_dump())
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def list(self, fiscal_year: Optional[int] = None) -> List[GLPeriod]:
        q = select(GLPeriod).order_by(GLPeriod.fiscal_year.desc(), GLPeriod.period_number)
        if fiscal_year:
            q = q.where(GLPeriod.fiscal_year == fiscal_year)
        return list(self.db.execute(q).scalars().all())

    def get(self, period_id: int) -> Optional[GLPeriod]:
        return self.db.get(GLPeriod, period_id)

    def close(self, period_id: int, user_id: int) -> GLPeriod:
        period = self._get_or_raise(period_id)
        if period.status != PeriodStatus.OPEN:
            raise ValueError(f"Period is {period.status.value}, cannot close")
        period.status = PeriodStatus.CLOSED
        period.closed_at = _utcnow()
        period.closed_by = user_id
        self.db.commit()
        self.db.refresh(period)
        return period

    def lock(self, period_id: int, user_id: int) -> GLPeriod:
        period = self._get_or_raise(period_id)
        if period.status == PeriodStatus.LOCKED:
            raise ValueError("Period is already locked")
        period.status = PeriodStatus.LOCKED
        period.locked_at = _utcnow()
        period.locked_by = user_id
        self.db.commit()
        self.db.refresh(period)
        return period

    def reopen(self, period_id: int) -> GLPeriod:
        period = self._get_or_raise(period_id)
        if period.status != PeriodStatus.CLOSED:
            raise ValueError(f"Period is {period.status.value}, only closed periods can be reopened")
        period.status = PeriodStatus.OPEN
        period.closed_at = None
        period.closed_by = None
        self.db.commit()
        self.db.refresh(period)
        return period

    def _get_or_raise(self, period_id: int) -> GLPeriod:
        period = self.db.get(GLPeriod, period_id)
        if not period:
            raise ValueError(f"Period {period_id} not found")
        return period


# ── Account Service ───────────────────────────────────────────────────

class AccountService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: schemas.AccountCreate) -> GLAccount:
        existing = self.db.execute(
            select(GLAccount).where(GLAccount.code == data.code)
        ).scalar_one_or_none()
        if existing:
            raise ValueError(f"Account code {data.code} already exists")
        account = GLAccount(**data.model_dump())
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def list(self, account_type: Optional[str] = None, parent_id: Optional[int] = None) -> List[GLAccount]:
        q = select(GLAccount).order_by(GLAccount.code)
        if account_type:
            q = q.where(GLAccount.account_type == account_type)
        if parent_id is not None:
            q = q.where(GLAccount.parent_id == parent_id)
        else:
            q = q.where(GLAccount.parent_id.is_(None))
        return list(self.db.execute(q).scalars().all())

    def get_tree(self) -> List[Dict[str, Any]]:
        all_accounts = list(
            self.db.execute(
                select(GLAccount).order_by(GLAccount.code)
            ).scalars().all()
        )
        parent_map: Dict[int, List[GLAccount]] = {}
        for a in all_accounts:
            pid = a.parent_id or 0
            parent_map.setdefault(pid, []).append(a)

        def build_node(account: GLAccount) -> Dict[str, Any]:
            node = {
                "id": account.id, "code": account.code,
                "name_en": account.name_en, "account_type": account.account_type.value if hasattr(account.account_type, 'value') else account.account_type,
                "normal_balance": account.normal_balance.value if hasattr(account.normal_balance, 'value') else account.normal_balance,
                "level": account.level, "is_control": account.is_control,
                "is_active": account.is_active,
                "children": [build_node(c) for c in parent_map.get(account.id, [])],
            }
            return node

        roots = parent_map.get(0, [])
        return [build_node(r) for r in sorted(roots, key=lambda x: x.code)]

    def get(self, account_id: int) -> Optional[GLAccount]:
        return self.db.get(GLAccount, account_id)

    def get_by_code(self, code: str) -> Optional[GLAccount]:
        return self.db.execute(
            select(GLAccount).where(GLAccount.code == code)
        ).scalar_one_or_none()

    def update(self, account_id: int, data: schemas.AccountUpdate) -> GLAccount:
        account = self._get_or_raise(account_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(account, field, value)
        self.db.commit()
        self.db.refresh(account)
        return account

    def deactivate(self, account_id: int) -> GLAccount:
        account = self._get_or_raise(account_id)
        has_txns = self.db.execute(
            select(func.count(GLJournalLine.id)).where(
                GLJournalLine.account_id == account_id
            )
        ).scalar() or 0
        if has_txns > 0:
            raise ValueError(f"Cannot deactivate account {account.code}: {has_txns} journal lines exist")
        account.is_active = False
        self.db.commit()
        self.db.refresh(account)
        return account

    def generate_from_template(self, template_name: str, fiscal_year: int = 2026) -> int:
        """Generate COA accounts from an industry template."""
        accounts_data = get_default_accounts(template_name)
        count = 0
        code_map: Dict[str, int] = {}
        for acct_data in accounts_data:
            existing = self.db.execute(
                select(GLAccount).where(GLAccount.code == acct_data["code"])
            ).scalar_one_or_none()
            if existing:
                code_map[acct_data["code"]] = existing.id
                continue
            parent_code = None
            parent_id = None
            for code, pid in code_map.items():
                if acct_data["code"].startswith(code[:3]) and code != acct_data["code"]:
                    parent_code = code
                    parent_id = pid
            account = GLAccount(
                code=acct_data["code"],
                name_en=acct_data["name_en"],
                account_type=acct_data["type"],
                normal_balance=acct_data.get("normal_balance", "debit"),
                category=acct_data.get("category", "other"),
                is_control=acct_data.get("is_control", False),
                parent_id=parent_id,
                level=1 if parent_id else 0,
            )
            self.db.add(account)
            self.db.flush()
            code_map[acct_data["code"]] = account.id
            count += 1
        self.db.commit()
        return count

    def _get_or_raise(self, account_id: int) -> GLAccount:
        account = self.db.get(GLAccount, account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        return account


# ── Journal Service ───────────────────────────────────────────────────

class JournalService:
    def __init__(self, db: Session):
        self.db = db
        self._account_svc = AccountService(db)

    def create(self, data: schemas.JournalCreate, user_id: int = 0) -> GLJournal:
        period = self.db.get(GLPeriod, data.period_id)
        if not period:
            raise ValueError(f"Period {data.period_id} not found")
        if period.status != PeriodStatus.OPEN:
            raise ValueError(f"Period {period.name} is {period.status.value}, journals cannot be posted")

        total_debit = sum(l.debit_amount for l in data.lines)
        total_credit = sum(l.credit_amount for l in data.lines)

        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(f"Journal not balanced: debits={total_debit:.2f}, credits={total_credit:.2f}")
        if total_debit == 0:
            raise ValueError("Journal must have at least one line with amount")

        for line_data in data.lines:
            account = self.db.get(GLAccount, line_data.account_id)
            if not account:
                raise ValueError(f"Account {line_data.account_id} not found")
            if not account.allow_manual_entry:
                raise ValueError(f"Account {account.code} {account.name_en} does not allow manual entries")

        journal_number = _generate_journal_number(self.db, period.fiscal_year)
        journal = GLJournal(
            journal_number=journal_number,
            period_id=data.period_id,
            journal_date=data.journal_date,
            description=data.description,
            source=data.source,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            is_adjusting=data.is_adjusting,
            branch_id=data.branch_id,
            entity_id=data.entity_id,
            total_debit=total_debit,
            total_credit=total_credit,
            created_by=user_id,
        )
        self.db.add(journal)
        self.db.flush()

        for line_data in data.lines:
            line = GLJournalLine(
                journal_id=journal.id,
                account_id=line_data.account_id,
                line_description=line_data.line_description,
                debit_amount=line_data.debit_amount,
                credit_amount=line_data.credit_amount,
                currency_id=line_data.currency_id,
                exchange_rate=line_data.exchange_rate,
                base_amount=line_data.debit_amount * line_data.exchange_rate or line_data.credit_amount * line_data.exchange_rate,
                cost_center_id=line_data.cost_center_id,
                project_id=line_data.project_id,
                branch_id=line_data.branch_id or data.branch_id,
                entity_id=line_data.entity_id or data.entity_id,
            )
            self.db.add(line)

        self.db.commit()
        self.db.refresh(journal)
        return journal

    def list(self, period_id: Optional[int] = None, status: Optional[str] = None,
             page: int = 1, page_size: int = 20) -> Tuple[List[GLJournal], int]:
        q = select(GLJournal).order_by(GLJournal.journal_date.desc(), GLJournal.id.desc())
        if period_id:
            q = q.where(GLJournal.period_id == period_id)
        if status:
            q = q.where(GLJournal.status == status)
        total = self.db.execute(select(func.count()).select_from(GLJournal).where(
            *(q.whereclause.clauses if q.whereclause else [])
        )).scalar() or 0
        q = q.offset((page - 1) * page_size).limit(page_size)
        journals = list(self.db.execute(q).scalars().all())
        return journals, total

    def get(self, journal_id: int) -> Optional[GLJournal]:
        return self.db.get(GLJournal, journal_id)

    def get_by_number(self, journal_number: str) -> Optional[GLJournal]:
        return self.db.execute(
            select(GLJournal).where(GLJournal.journal_number == journal_number)
        ).scalar_one_or_none()

    def post(self, journal_id: int, user_id: int = 0) -> GLJournal:
        journal = self._get_or_raise(journal_id)
        if journal.status != JournalStatus.DRAFT:
            raise ValueError(f"Journal {journal.journal_number} is already {journal.status.value}")
        period = self.db.get(GLPeriod, journal.period_id)
        if period and period.status != PeriodStatus.OPEN:
            raise ValueError(f"Period {period.name} is {period.status.value}, cannot post")
        journal.status = JournalStatus.POSTED
        journal.posted_at = _utcnow()
        journal.posted_by = user_id
        self.db.commit()
        self.db.refresh(journal)
        return journal

    def reverse(self, journal_id: int, data: schemas.JournalReverse, user_id: int = 0) -> GLJournal:
        journal = self._get_or_raise(journal_id)
        if journal.status != JournalStatus.POSTED:
            raise ValueError(f"Only posted journals can be reversed (status: {journal.status.value})")
        period = self.db.get(GLPeriod, journal.period_id)
        if not period:
            raise ValueError("Period not found")
        journal_lines = self.db.execute(
            select(GLJournalLine).where(GLJournalLine.journal_id == journal_id)
        ).scalars().all()

        reversal_lines = []
        for line in journal_lines:
            reversal_lines.append(schemas.JournalLineCreate(
                account_id=line.account_id,
                line_description=f"Reversal: {line.line_description or journal.description}",
                debit_amount=line.credit_amount,
                credit_amount=line.debit_amount,
                currency_id=line.currency_id,
                exchange_rate=line.exchange_rate,
                cost_center_id=line.cost_center_id,
                project_id=line.project_id,
                branch_id=line.branch_id,
                entity_id=line.entity_id,
            ))

        rev_data = schemas.JournalCreate(
            period_id=journal.period_id,
            journal_date=data.reversal_date,
            description=data.description or f"Reversal of {journal.journal_number}",
            source="reversal",
            reference_type="reversal",
            reference_id=journal.id,
            is_adjusting=journal.is_adjusting,
            branch_id=journal.branch_id,
            entity_id=journal.entity_id,
            lines=reversal_lines,
        )
        reversal = self.create(rev_data, user_id)
        self.post(reversal.id, user_id)

        journal.status = JournalStatus.REVERSED
        journal.reversed_journal_id = reversal.id
        journal.reversal_date = data.reversal_date
        self.db.commit()
        self.db.refresh(journal)
        return journal

    def _get_or_raise(self, journal_id: int) -> GLJournal:
        journal = self.db.get(GLJournal, journal_id)
        if not journal:
            raise ValueError(f"Journal {journal_id} not found")
        return journal


# ── Trial Balance Service ─────────────────────────────────────────────

class TrialBalanceService:
    def __init__(self, db: Session):
        self.db = db

    def calculate(self, period_id: int) -> List[GLTrialBalance]:
        period = self.db.get(GLPeriod, period_id)
        if not period:
            raise ValueError(f"Period {period_id} not found")

        # Remove existing TB for this period
        self.db.execute(
            select(GLTrialBalance).where(GLTrialBalance.period_id == period_id)
        ).scalars().all()
        self.db.execute(
            GLTrialBalance.__table__.delete().where(GLTrialBalance.period_id == period_id)
        )
        self.db.flush()

        # Get all active accounts
        accounts = list(
            self.db.execute(
                select(GLAccount).where(GLAccount.is_active == True).order_by(GLAccount.code)
            ).scalars().all()
        )

        # Get carry-forward from previous period
        prev_period = self.db.execute(
            select(GLPeriod).where(
                GLPeriod.fiscal_year == period.fiscal_year,
                GLPeriod.period_number == period.period_number - 1,
            )
        ).scalar_one_or_none()

        prev_tb: Dict[int, Tuple[float, float]] = {}
        if prev_period:
            prev_records = list(
                self.db.execute(
                    select(GLTrialBalance).where(
                        GLTrialBalance.period_id == prev_period.id
                    )
                ).scalars().all()
            )
            for r in prev_records:
                prev_tb[r.account_id] = (r.closing_debit, r.closing_credit)

        # Get journal lines for this period
        period_lines = list(
            self.db.execute(
                select(GLJournalLine).join(GLJournal).where(
                    GLJournal.period_id == period_id,
                    GLJournal.status == JournalStatus.POSTED,
                )
            ).scalars().all()
        )

        # Aggregate by account
        turnover: Dict[int, Tuple[float, float]] = {}
        for line in period_lines:
            d, c = turnover.get(line.account_id, (0.0, 0.0))
            turnover[line.account_id] = (d + line.debit_amount, c + line.credit_amount)

        tb_records = []
        for account in accounts:
            op_debit, op_credit = prev_tb.get(account.id, (0.0, 0.0))
            dr_turn, cr_turn = turnover.get(account.id, (0.0, 0.0))

            if account.normal_balance.value == "debit":
                closing_debit = op_debit + dr_turn - cr_turn
                closing_credit = 0.0
                if closing_debit < 0:
                    closing_credit = abs(closing_debit)
                    closing_debit = 0.0
            else:
                closing_credit = op_credit + cr_turn - dr_turn
                closing_debit = 0.0
                if closing_credit < 0:
                    closing_debit = abs(closing_credit)
                    closing_credit = 0.0

            tb = GLTrialBalance(
                period_id=period_id,
                account_id=account.id,
                opening_debit=op_debit,
                opening_credit=op_credit,
                debit_turnover=dr_turn,
                credit_turnover=cr_turn,
                closing_debit=closing_debit,
                closing_credit=closing_credit,
            )
            self.db.add(tb)
            tb_records.append(tb)

        self.db.commit()
        for tb in tb_records:
            self.db.refresh(tb)
        return tb_records

    def get(self, period_id: int) -> List[GLTrialBalance]:
        records = list(
            self.db.execute(
                select(GLTrialBalance)
                .where(GLTrialBalance.period_id == period_id)
                .order_by(GLTrialBalance.id)
            ).scalars().all()
        )
        if not records:
            records = self.calculate(period_id)
        return records

    def validate(self, period_id: int) -> Dict[str, Any]:
        records = self.get(period_id)
        total_debit = sum(r.closing_debit for r in records)
        total_credit = sum(r.closing_credit for r in records)
        diff = abs(total_debit - total_credit)

        unbalanced = []
        for r in records:
            if r.closing_debit > 0 and r.closing_credit > 0:
                unbalanced.append(f"Account {r.account_id}: both debit ({r.closing_debit}) and credit ({r.closing_credit})")

        return {
            "period_id": period_id,
            "total_accounts": len(records),
            "total_debit": total_debit,
            "total_credit": total_credit,
            "difference": round(diff, 2),
            "is_balanced": diff < 0.01,
            "unbalanced_accounts": unbalanced,
        }


# ── Adjusting Entry Service ───────────────────────────────────────────

class AdjustingEntryService:
    def __init__(self, db: Session):
        self.db = db
        self._journal_svc = JournalService(db)

    def create(self, data: schemas.AdjustingEntryCreate, user_id: int = 0) -> GLAdjustingEntry:
        period = self.db.get(GLPeriod, data.period_id)
        if not period:
            raise ValueError(f"Period {data.period_id} not found")

        total_debit = sum(l.debit_amount for l in data.lines)
        total_credit = sum(l.credit_amount for l in data.lines)
        if abs(total_debit - total_credit) > 0.01:
            raise ValueError(f"Adjusting entry not balanced: debits={total_debit:.2f}, credits={total_credit:.2f}")

        entry_number = _generate_adjusting_number(self.db, period.fiscal_year)
        entry = GLAdjustingEntry(
            entry_number=entry_number,
            period_id=data.period_id,
            entry_type=data.entry_type,
            description=data.description,
            total_debit=total_debit,
            total_credit=total_credit,
            notes=data.notes,
            created_by=user_id,
        )
        self.db.add(entry)
        self.db.flush()

        for line_data in data.lines:
            line = GLAdjustingEntryLine(
                adjusting_entry_id=entry.id,
                account_id=line_data.account_id,
                line_description=line_data.line_description,
                debit_amount=line_data.debit_amount,
                credit_amount=line_data.credit_amount,
            )
            self.db.add(line)

        self.db.commit()
        self.db.refresh(entry)
        return entry

    def list(self, period_id: Optional[int] = None) -> List[GLAdjustingEntry]:
        q = select(GLAdjustingEntry).order_by(GLAdjustingEntry.id.desc())
        if period_id:
            q = q.where(GLAdjustingEntry.period_id == period_id)
        return list(self.db.execute(q).scalars().all())

    def get(self, entry_id: int) -> Optional[GLAdjustingEntry]:
        return self.db.get(GLAdjustingEntry, entry_id)

    def approve(self, entry_id: int, user_id: int) -> GLAdjustingEntry:
        entry = self._get_or_raise(entry_id)
        if entry.status != AdjustingEntryStatus.DRAFT:
            raise ValueError(f"Entry {entry.entry_number} is already {entry.status.value}")
        entry.status = AdjustingEntryStatus.APPROVED
        entry.approved_by = user_id
        entry.approved_at = _utcnow()
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def post(self, entry_id: int, user_id: int = 0) -> GLAdjustingEntry:
        entry = self._get_or_raise(entry_id)
        if entry.status != AdjustingEntryStatus.APPROVED:
            raise ValueError(f"Entry {entry.entry_number} must be approved first (status: {entry.status.value})")

        lines = list(
            self.db.execute(
                select(GLAdjustingEntryLine).where(
                    GLAdjustingEntryLine.adjusting_entry_id == entry_id
                )
            ).scalars().all()
        )

        journal_data = schemas.JournalCreate(
            period_id=entry.period_id,
            journal_date=date.today(),
            description=f"Adjusting: {entry.description or entry.entry_type.value} ({entry.entry_number})",
            source="adjusting",
            reference_type="adjusting_entry",
            reference_id=entry.id,
            is_adjusting=True,
            lines=[
                schemas.JournalLineCreate(
                    account_id=l.account_id,
                    line_description=l.line_description,
                    debit_amount=l.debit_amount,
                    credit_amount=l.credit_amount,
                ) for l in lines
            ],
        )
        journal = self._journal_svc.create(journal_data, user_id)
        self._journal_svc.post(journal.id, user_id)

        entry.status = AdjustingEntryStatus.POSTED
        entry.journal_id = journal.id
        entry.posted_at = _utcnow()
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def _get_or_raise(self, entry_id: int) -> GLAdjustingEntry:
        entry = self.db.get(GLAdjustingEntry, entry_id)
        if not entry:
            raise ValueError(f"Adjusting entry {entry_id} not found")
        return entry


# ── Financial Report Service ──────────────────────────────────────────

class FinancialReportService:
    def __init__(self, db: Session):
        self.db = db
        self._tb_svc = TrialBalanceService(db)

    def balance_sheet(self, period_id: int) -> Dict[str, Any]:
        period = self.db.get(GLPeriod, period_id)
        if not period:
            raise ValueError(f"Period {period_id} not found")
        tb = self._tb_svc.get(period_id)
        accounts = {a.id: a for a in self.db.execute(select(GLAccount)).scalars().all()}

        lines = []
        total_assets = 0.0
        total_liabilities = 0.0
        total_equity = 0.0

        for record in tb:
            account = accounts.get(record.account_id)
            if not account:
                continue
            balance = record.closing_debit - record.closing_credit

            atype = account.account_type.value if hasattr(account.account_type, 'value') else account.account_type
            if atype == "asset":
                total_assets += balance if balance > 0 else 0
            elif atype == "liability":
                total_liabilities += abs(balance) if balance < 0 else balance
            elif atype == "equity":
                total_equity += balance

            lines.append({
                "account_code": account.code, "account_name": account.name_en,
                "account_type": atype, "category": account.category.value if hasattr(account.category, 'value') else account.category,
                "balance": balance, "is_control": account.is_control, "level": account.level,
            })

        diff = abs(total_assets - (total_liabilities + total_equity))
        return {
            "period_id": period_id, "period_name": period.name,
            "as_of_date": period.end_date.isoformat(),
            "lines": lines, "total_assets": total_assets,
            "total_liabilities": total_liabilities, "total_equity": total_equity,
            "check": "BALANCED" if diff < 0.01 else f"OFF BY {diff:.2f}",
        }

    def profit_loss(self, period_id: int) -> Dict[str, Any]:
        period = self.db.get(GLPeriod, period_id)
        if not period:
            raise ValueError(f"Period {period_id} not found")
        tb = self._tb_svc.get(period_id)
        accounts = {a.id: a for a in self.db.execute(select(GLAccount)).scalars().all()}

        lines = []
        total_revenue = 0.0
        total_cogs = 0.0
        total_opex = 0.0

        for record in tb:
            account = accounts.get(record.account_id)
            if not account:
                continue
            balance = record.closing_credit - record.closing_debit

            atype = account.account_type.value if hasattr(account.account_type, 'value') else account.account_type
            cat = account.category.value if hasattr(account.category, 'value') else account.category

            if atype == "revenue":
                total_revenue += balance if balance > 0 else 0
            elif cat == "cogs":
                total_cogs += abs(balance) if balance < 0 else balance
            elif atype == "expense":
                total_opex += abs(balance) if balance < 0 else balance

            lines.append({
                "account_code": account.code, "account_name": account.name_en,
                "account_type": atype, "balance": balance, "category": cat,
            })

        gross_profit = total_revenue - total_cogs
        net_income = gross_profit - total_opex
        return {
            "period_id": period_id, "period_name": period.name,
            "start_date": period.start_date.isoformat(), "end_date": period.end_date.isoformat(),
            "lines": lines, "total_revenue": total_revenue,
            "total_cogs": total_cogs, "gross_profit": gross_profit,
            "total_opex": total_opex, "net_income": net_income,
            "check": "PROFIT" if net_income >= 0 else "LOSS",
        }


# ── Year-End Close Service ────────────────────────────────────────────

class YearEndCloseService:
    STAGES = [s.value for s in YearEndStage]

    def __init__(self, db: Session):
        self.db = db
        self._journal_svc = JournalService(db)
        self._tb_svc = TrialBalanceService(db)

    def start(self, data: schemas.YearEndCloseStart, user_id: int = 0) -> GLYearEndClose:
        existing = self.db.execute(
            select(GLYearEndClose).where(GLYearEndClose.fiscal_year == data.fiscal_year)
        ).scalar_one_or_none()
        if existing:
            raise ValueError(f"Year-end close for {data.fiscal_year} already exists (status: {existing.status})")

        close = GLYearEndClose(
            fiscal_year=data.fiscal_year,
            status="in_progress",
            stages_completed={},
            closing_period_id=data.closing_period_id,
            opening_period_id=data.opening_period_id,
            income_summary_account_id=data.income_summary_account_id,
            retained_earnings_account_id=data.retained_earnings_account_id,
            started_at=_utcnow(),
            completed_by=user_id,
            notes=data.notes,
            created_by=user_id,
        )
        self.db.add(close)
        self.db.commit()
        self.db.refresh(close)
        return close

    def complete_stage(self, close_id: int, stage: str, user_id: int = 0) -> GLYearEndClose:
        close = self._get_or_raise(close_id)
        if close.status != "in_progress":
            raise ValueError(f"Year-end close is {close.status}")
        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}. Valid: {', '.join(self.STAGES)}")

        stages = dict(close.stages_completed or {})
        stages[stage] = {"completed_at": _utcnow().isoformat(), "completed_by": user_id}
        close.stages_completed = stages

        if stage == YearEndStage.FINAL_TRIAL_BALANCE.value:
            tb = self._tb_svc.calculate(close.closing_period_id)
            total_rev = sum(abs(r.closing_credit) for r in tb
                if self.db.get(GLAccount, r.account_id) and
                getattr(self.db.get(GLAccount, r.account_id), 'account_type', None) and
                self.db.get(GLAccount, r.account_id).account_type.value == "revenue")
            total_exp = sum(abs(r.closing_debit) for r in tb
                if self.db.get(GLAccount, r.account_id) and
                getattr(self.db.get(GLAccount, r.account_id), 'account_type', None) and
                self.db.get(GLAccount, r.account_id).account_type.value == "expense")
            close.total_revenue = total_rev
            close.total_expenses = total_exp
            close.net_income = total_rev - total_exp

        if stage == YearEndStage.LOCK_PERIOD.value:
            close.status = "completed"
            close.completed_at = _utcnow()
            period = self.db.get(GLPeriod, close.closing_period_id)
            if period:
                period.status = PeriodStatus.LOCKED
                period.locked_at = _utcnow()
                period.locked_by = user_id

        self.db.commit()
        self.db.refresh(close)
        return close

    def get(self, fiscal_year: int) -> Optional[GLYearEndClose]:
        return self.db.execute(
            select(GLYearEndClose).where(GLYearEndClose.fiscal_year == fiscal_year)
        ).scalar_one_or_none()

    def _get_or_raise(self, close_id: int) -> GLYearEndClose:
        close = self.db.get(GLYearEndClose, close_id)
        if not close:
            raise ValueError(f"Year-end close {close_id} not found")
        return close


# ── Health Service ────────────────────────────────────────────────────

class HealthService:
    def __init__(self, db: Session):
        self.db = db

    def check(self) -> Dict[str, Any]:
        metrics = []

        # 1. Periods count
        period_count = self.db.execute(select(func.count(GLPeriod.id))).scalar() or 0
        metrics.append({"name": "periods_total", "status": "ok" if period_count > 0 else "warn",
                        "value": period_count, "details": "Fiscal periods defined"})

        # 2. Open periods
        open_periods = self.db.execute(
            select(func.count(GLPeriod.id)).where(GLPeriod.status == PeriodStatus.OPEN)
        ).scalar() or 0
        metrics.append({"name": "periods_open", "status": "ok" if open_periods > 0 else "warn",
                        "value": open_periods, "details": "Open periods available for posting"})

        # 3. Account count
        account_count = self.db.execute(select(func.count(GLAccount.id))).scalar() or 0
        metrics.append({"name": "accounts_total", "status": "ok" if account_count > 0 else "warn",
                        "value": account_count, "details": "Chart of accounts"})

        # 4. Active accounts
        active_accounts = self.db.execute(
            select(func.count(GLAccount.id)).where(GLAccount.is_active == True)
        ).scalar() or 0
        metrics.append({"name": "accounts_active", "status": "ok", "value": active_accounts})

        # 5. Journal count
        journal_count = self.db.execute(select(func.count(GLJournal.id))).scalar() or 0
        metrics.append({"name": "journals_total", "status": "ok", "value": journal_count})

        # 6. Unbalanced journals
        unbalanced = self.db.execute(
            select(func.count(GLJournal.id)).where(
                GLJournal.status == JournalStatus.DRAFT,
                GLJournal.total_debit != GLJournal.total_credit,
            )
        ).scalar() or 0
        metrics.append({"name": "journals_unbalanced", "status": "ok" if unbalanced == 0 else "warn",
                        "value": unbalanced, "details": "Draft journals where debits != credits"})

        # 7. Periods with TB calculated
        tb_periods = self.db.execute(
            select(func.count(func.distinct(GLTrialBalance.period_id)))
        ).scalar() or 0
        metrics.append({"name": "tb_periods", "status": "ok", "value": tb_periods})

        # 8. Year-end close status
        ye_close = self.db.execute(
            select(GLYearEndClose).order_by(GLYearEndClose.fiscal_year.desc()).limit(1)
        ).scalar_one_or_none()
        metrics.append({"name": "latest_year_end", "status": ye_close.status if ye_close else "warn",
                        "value": ye_close.fiscal_year if ye_close else "none",
                        "details": f"Status: {ye_close.status if ye_close else 'no year-end close found'}"})

        # 9. Adjusting entries pending
        pending_adj = self.db.execute(
            select(func.count(GLAdjustingEntry.id)).where(
                GLAdjustingEntry.status == AdjustingEntryStatus.DRAFT
            )
        ).scalar() or 0
        metrics.append({"name": "adjusting_entries_pending", "status": "ok",
                        "value": pending_adj, "details": "Adjusting entries awaiting approval"})

        # 10. Overall
        has_issues = any(m["status"] == "warn" for m in metrics)
        overall = "degraded" if has_issues else "healthy"

        return {"status": overall, "module": "far-gl", "version": "1.0.0", "metrics": metrics}
