"""
FAR-GL Router — 30+ FastAPI endpoints for General Ledger.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_sync_session
from app.organs.far_gl_organ import schemas
from app.organs.far_gl_organ.service import (
    PeriodService, AccountService, JournalService,
    TrialBalanceService, AdjustingEntryService,
    FinancialReportService, YearEndCloseService, HealthService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["far-gl"])


def get_db():
    db = get_sync_session()
    try:
        yield db
    finally:
        db.close()


def _ok(message: str, id: Optional[int] = None) -> schemas.MessageResponse:
    return schemas.MessageResponse(message=message, id=id)


# ── Period Endpoints ────────────────────────────────────────────────────


@router.post("/periods", response_model=schemas.PeriodResponse, status_code=201)
def create_period(data: schemas.PeriodCreate, db: Session = Depends(get_db)):
    svc = PeriodService(db)
    try:
        period = svc.create(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.PeriodResponse(
        id=period.id, fiscal_year=period.fiscal_year,
        period_number=period.period_number, name=period.name,
        start_date=period.start_date, end_date=period.end_date,
        status=period.status.value, is_adjustment_period=period.is_adjustment_period,
        is_active=period.is_active, created_at=period.created_at,
    )


@router.get("/periods", response_model=schemas.PeriodListResponse)
def list_periods(
    fiscal_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    svc = PeriodService(db)
    periods = svc.list(fiscal_year)
    return schemas.PeriodListResponse(
        periods=[
            schemas.PeriodResponse(
                id=p.id, fiscal_year=p.fiscal_year,
                period_number=p.period_number, name=p.name,
                start_date=p.start_date, end_date=p.end_date,
                status=p.status.value,
                is_adjustment_period=p.is_adjustment_period,
                is_active=p.is_active, created_at=p.created_at,
            )
            for p in periods
        ],
        total=len(periods),
    )


@router.get("/periods/{period_id}", response_model=schemas.PeriodResponse)
def get_period(period_id: int, db: Session = Depends(get_db)):
    svc = PeriodService(db)
    period = svc.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    return schemas.PeriodResponse(
        id=period.id, fiscal_year=period.fiscal_year,
        period_number=period.period_number, name=period.name,
        start_date=period.start_date, end_date=period.end_date,
        status=period.status.value,
        is_adjustment_period=period.is_adjustment_period,
        is_active=period.is_active, created_at=period.created_at,
    )


@router.post("/periods/{period_id}/close", response_model=schemas.PeriodResponse)
def close_period(
    period_id: int, user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    svc = PeriodService(db)
    try:
        period = svc.close(period_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.PeriodResponse(
        id=period.id, fiscal_year=period.fiscal_year,
        period_number=period.period_number, name=period.name,
        start_date=period.start_date, end_date=period.end_date,
        status=period.status.value,
        is_adjustment_period=period.is_adjustment_period,
        is_active=period.is_active, created_at=period.created_at,
    )


@router.post("/periods/{period_id}/lock", response_model=schemas.PeriodResponse)
def lock_period(
    period_id: int, user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    svc = PeriodService(db)
    try:
        period = svc.lock(period_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.PeriodResponse(
        id=period.id, fiscal_year=period.fiscal_year,
        period_number=period.period_number, name=period.name,
        start_date=period.start_date, end_date=period.end_date,
        status=period.status.value,
        is_adjustment_period=period.is_adjustment_period,
        is_active=period.is_active, created_at=period.created_at,
    )


@router.post("/periods/{period_id}/reopen", response_model=schemas.PeriodResponse)
def reopen_period(period_id: int, db: Session = Depends(get_db)):
    svc = PeriodService(db)
    try:
        period = svc.reopen(period_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.PeriodResponse(
        id=period.id, fiscal_year=period.fiscal_year,
        period_number=period.period_number, name=period.name,
        start_date=period.start_date, end_date=period.end_date,
        status=period.status.value,
        is_adjustment_period=period.is_adjustment_period,
        is_active=period.is_active, created_at=period.created_at,
    )


# ── Account Endpoints ───────────────────────────────────────────────────


@router.post("/accounts", response_model=schemas.AccountResponse, status_code=201)
def create_account(data: schemas.AccountCreate, db: Session = Depends(get_db)):
    svc = AccountService(db)
    try:
        account = svc.create(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    children_count = len(account.children) if hasattr(account, 'children') else 0
    return schemas.AccountResponse(
        id=account.id, code=account.code, name_en=account.name_en,
        name_ar=account.name_ar, account_type=account.account_type.value,
        normal_balance=account.normal_balance.value, category=account.category.value,
        is_control=account.is_control, parent_id=account.parent_id,
        level=account.level, is_active=account.is_active,
        allow_manual_entry=account.allow_manual_entry,
        created_at=account.created_at, children_count=children_count,
    )


@router.get("/accounts", response_model=List[schemas.AccountResponse])
def list_accounts(
    account_type: Optional[str] = Query(None),
    parent_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    svc = AccountService(db)
    accounts = svc.list(account_type, parent_id)
    result = []
    for a in accounts:
        children_count = len(a.children) if hasattr(a, 'children') else 0
        result.append(schemas.AccountResponse(
            id=a.id, code=a.code, name_en=a.name_en, name_ar=a.name_ar,
            account_type=a.account_type.value,
            normal_balance=a.normal_balance.value,
            category=a.category.value, is_control=a.is_control,
            parent_id=a.parent_id, level=a.level, is_active=a.is_active,
            allow_manual_entry=a.allow_manual_entry,
            created_at=a.created_at, children_count=children_count,
        ))
    return result


@router.get("/accounts/tree", response_model=List[schemas.AccountTreeNode])
def get_account_tree(db: Session = Depends(get_db)):
    svc = AccountService(db)
    return svc.get_tree()


@router.get("/accounts/{account_id}", response_model=schemas.AccountResponse)
def get_account(account_id: int, db: Session = Depends(get_db)):
    svc = AccountService(db)
    account = svc.get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    children_count = len(account.children) if hasattr(account, 'children') else 0
    return schemas.AccountResponse(
        id=account.id, code=account.code, name_en=account.name_en,
        name_ar=account.name_ar, account_type=account.account_type.value,
        normal_balance=account.normal_balance.value,
        category=account.category.value, is_control=account.is_control,
        parent_id=account.parent_id, level=account.level,
        is_active=account.is_active,
        allow_manual_entry=account.allow_manual_entry,
        created_at=account.created_at, children_count=children_count,
    )


@router.get("/accounts/by-code/{code}", response_model=schemas.AccountResponse)
def get_account_by_code(code: str, db: Session = Depends(get_db)):
    svc = AccountService(db)
    account = svc.get_by_code(code)
    if not account:
        raise HTTPException(404, "Account not found")
    children_count = len(account.children) if hasattr(account, 'children') else 0
    return schemas.AccountResponse(
        id=account.id, code=account.code, name_en=account.name_en,
        name_ar=account.name_ar, account_type=account.account_type.value,
        normal_balance=account.normal_balance.value,
        category=account.category.value, is_control=account.is_control,
        parent_id=account.parent_id, level=account.level,
        is_active=account.is_active,
        allow_manual_entry=account.allow_manual_entry,
        created_at=account.created_at, children_count=children_count,
    )


@router.put("/accounts/{account_id}", response_model=schemas.AccountResponse)
def update_account(
    account_id: int, data: schemas.AccountUpdate,
    db: Session = Depends(get_db),
):
    svc = AccountService(db)
    try:
        account = svc.update(account_id, data)
    except ValueError as e:
        raise HTTPException(404, str(e))
    children_count = len(account.children) if hasattr(account, 'children') else 0
    return schemas.AccountResponse(
        id=account.id, code=account.code, name_en=account.name_en,
        name_ar=account.name_ar, account_type=account.account_type.value,
        normal_balance=account.normal_balance.value,
        category=account.category.value, is_control=account.is_control,
        parent_id=account.parent_id, level=account.level,
        is_active=account.is_active,
        allow_manual_entry=account.allow_manual_entry,
        created_at=account.created_at, children_count=children_count,
    )


@router.delete("/accounts/{account_id}/deactivate")
def deactivate_account(account_id: int, db: Session = Depends(get_db)):
    svc = AccountService(db)
    try:
        svc.deactivate(account_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _ok("Account deactivated", account_id)


@router.post("/accounts/generate-from-template")
def generate_accounts_from_template(
    data: schemas.COATemplateGenerate,
    db: Session = Depends(get_db),
):
    svc = AccountService(db)
    count = svc.generate_from_template(data.template_name, data.fiscal_year)
    return _ok(f"Generated {count} accounts from template '{data.template_name}'")


# ── Journal Endpoints ───────────────────────────────────────────────────


@router.post("/journals", response_model=schemas.JournalResponse, status_code=201)
def create_journal(
    data: schemas.JournalCreate, user_id: int = Query(0),
    db: Session = Depends(get_db),
):
    svc = JournalService(db)
    try:
        journal = svc.create(data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _journal_to_response(journal, db)


@router.get("/journals", response_model=schemas.JournalListResponse)
def list_journals(
    period_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    svc = JournalService(db)
    journals, total = svc.list(period_id, status, page, page_size)
    return schemas.JournalListResponse(
        journals=[_journal_to_response(j, db) for j in journals],
        total=total, page=page, page_size=page_size,
    )


@router.get("/journals/{journal_id}", response_model=schemas.JournalResponse)
def get_journal(journal_id: int, db: Session = Depends(get_db)):
    svc = JournalService(db)
    journal = svc.get(journal_id)
    if not journal:
        raise HTTPException(404, "Journal not found")
    return _journal_to_response(journal, db)


@router.get("/journals/by-number/{journal_number}", response_model=schemas.JournalResponse)
def get_journal_by_number(journal_number: str, db: Session = Depends(get_db)):
    svc = JournalService(db)
    journal = svc.get_by_number(journal_number)
    if not journal:
        raise HTTPException(404, "Journal not found")
    return _journal_to_response(journal, db)


@router.post("/journals/{journal_id}/post", response_model=schemas.JournalResponse)
def post_journal(
    journal_id: int, user_id: int = Query(0),
    db: Session = Depends(get_db),
):
    svc = JournalService(db)
    try:
        journal = svc.post(journal_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _journal_to_response(journal, db)


@router.post("/journals/{journal_id}/reverse", response_model=schemas.JournalResponse)
def reverse_journal(
    journal_id: int, data: schemas.JournalReverse,
    user_id: int = Query(0), db: Session = Depends(get_db),
):
    svc = JournalService(db)
    try:
        journal = svc.reverse(journal_id, data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _journal_to_response(journal, db)


def _journal_to_response(journal, db: Session) -> schemas.JournalResponse:
    lines = []
    for line in journal.lines:
        account = line.account
        lines.append(schemas.JournalLineResponse(
            id=line.id, account_id=line.account_id,
            account_code=account.code if account else "",
            account_name=account.name_en if account else "",
            line_description=line.line_description,
            debit_amount=line.debit_amount,
            credit_amount=line.credit_amount,
            currency_id=line.currency_id,
        ))
    return schemas.JournalResponse(
        id=journal.id, journal_number=journal.journal_number,
        period_id=journal.period_id, journal_date=journal.journal_date,
        description=journal.description, status=journal.status.value,
        total_debit=journal.total_debit, total_credit=journal.total_credit,
        source=journal.source, posted_at=journal.posted_at,
        is_adjusting=journal.is_adjusting, created_at=journal.created_at,
        lines=lines,
    )


# ── Trial Balance Endpoints ──────────────────────────────────────────────


@router.post("/trial-balance/calculate/{period_id}")
def calculate_trial_balance(period_id: int, db: Session = Depends(get_db)):
    svc = TrialBalanceService(db)
    try:
        records = svc.calculate(period_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _ok(f"Trial balance calculated for period {period_id} with {len(records)} accounts", period_id)


@router.get("/trial-balance/{period_id}", response_model=schemas.TrialBalanceResponse)
def get_trial_balance(period_id: int, db: Session = Depends(get_db)):
    svc = TrialBalanceService(db)
    period_svc = PeriodService(db)
    try:
        records = svc.get(period_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    period = period_svc.get(period_id)
    if not period:
        raise HTTPException(404, "Period not found")
    total_debit = sum(r.closing_debit for r in records)
    total_credit = sum(r.closing_credit for r in records)
    calc_at = records[0].calculated_at if records else date.today()
    accounts = {}
    for r in records:
        a = r.account
        if a:
            accounts[r.account_id] = a
    lines = []
    for r in records:
        a = accounts.get(r.account_id)
        lines.append(schemas.TrialBalanceLine(
            account_id=r.account_id,
            account_code=a.code if a else "",
            account_name=a.name_en if a else "",
            account_type=a.account_type.value if a else "",
            opening_debit=r.opening_debit, opening_credit=r.opening_credit,
            debit_turnover=r.debit_turnover, credit_turnover=r.credit_turnover,
            closing_debit=r.closing_debit, closing_credit=r.closing_credit,
        ))
    diff = abs(total_debit - total_credit)
    return schemas.TrialBalanceResponse(
        period_id=period_id, period_name=period.name,
        fiscal_year=period.fiscal_year, period_number=period.period_number,
        lines=lines, total_debit=total_debit, total_credit=total_credit,
        is_balanced=diff < 0.01, difference=round(diff, 2),
        calculated_at=calc_at,
    )


@router.get("/trial-balance/{period_id}/validate")
def validate_trial_balance(period_id: int, db: Session = Depends(get_db)):
    svc = TrialBalanceService(db)
    try:
        result = svc.validate(period_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return result


# ── Adjusting Entry Endpoints ────────────────────────────────────────────


@router.post("/adjusting-entries", response_model=schemas.AdjustingEntryResponse, status_code=201)
def create_adjusting_entry(
    data: schemas.AdjustingEntryCreate, user_id: int = Query(0),
    db: Session = Depends(get_db),
):
    svc = AdjustingEntryService(db)
    try:
        entry = svc.create(data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _adjusting_to_response(entry, db)


@router.get("/adjusting-entries", response_model=List[schemas.AdjustingEntryResponse])
def list_adjusting_entries(
    period_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    svc = AdjustingEntryService(db)
    entries = svc.list(period_id)
    return [_adjusting_to_response(e, db) for e in entries]


@router.get("/adjusting-entries/{entry_id}", response_model=schemas.AdjustingEntryResponse)
def get_adjusting_entry(entry_id: int, db: Session = Depends(get_db)):
    svc = AdjustingEntryService(db)
    entry = svc.get(entry_id)
    if not entry:
        raise HTTPException(404, "Adjusting entry not found")
    return _adjusting_to_response(entry, db)


@router.post("/adjusting-entries/{entry_id}/approve", response_model=schemas.AdjustingEntryResponse)
def approve_adjusting_entry(
    entry_id: int, user_id: int = Query(1),
    db: Session = Depends(get_db),
):
    svc = AdjustingEntryService(db)
    try:
        entry = svc.approve(entry_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _adjusting_to_response(entry, db)


@router.post("/adjusting-entries/{entry_id}/post", response_model=schemas.AdjustingEntryResponse)
def post_adjusting_entry(
    entry_id: int, user_id: int = Query(0),
    db: Session = Depends(get_db),
):
    svc = AdjustingEntryService(db)
    try:
        entry = svc.post(entry_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _adjusting_to_response(entry, db)


def _adjusting_to_response(entry, db: Session) -> schemas.AdjustingEntryResponse:
    lines = []
    for line in entry.lines:
        account = line.account
        lines.append(schemas.AdjustingEntryLineResponse(
            id=line.id, account_id=line.account_id,
            account_code=account.code if account else "",
            account_name=account.name_en if account else "",
            line_description=line.line_description,
            debit_amount=line.debit_amount, credit_amount=line.credit_amount,
        ))
    return schemas.AdjustingEntryResponse(
        id=entry.id, entry_number=entry.entry_number,
        period_id=entry.period_id, entry_type=entry.entry_type.value if hasattr(entry.entry_type, 'value') else entry.entry_type,
        description=entry.description, status=entry.status.value,
        total_debit=entry.total_debit, total_credit=entry.total_credit,
        approved_by=entry.approved_by, posted_at=entry.posted_at,
        created_at=entry.created_at, lines=lines,
    )


# ── Financial Report Endpoints ───────────────────────────────────────────


@router.get("/reports/balance-sheet/{period_id}", response_model=schemas.BalanceSheetResponse)
def balance_sheet(period_id: int, db: Session = Depends(get_db)):
    svc = FinancialReportService(db)
    try:
        result = svc.balance_sheet(period_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.BalanceSheetResponse(
        period_id=result["period_id"], period_name=result["period_name"],
        as_of_date=result["as_of_date"], lines=result["lines"],
        total_assets=result["total_assets"],
        total_liabilities=result["total_liabilities"],
        total_equity=result["total_equity"], check=result["check"],
    )


@router.get("/reports/profit-loss/{period_id}", response_model=schemas.ProfitLossResponse)
def profit_loss(period_id: int, db: Session = Depends(get_db)):
    svc = FinancialReportService(db)
    try:
        result = svc.profit_loss(period_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.ProfitLossResponse(
        period_id=result["period_id"], period_name=result["period_name"],
        start_date=result["start_date"], end_date=result["end_date"],
        lines=result["lines"], total_revenue=result["total_revenue"],
        total_cogs=result["total_cogs"], gross_profit=result["gross_profit"],
        total_opex=result["total_opex"], net_income=result["net_income"],
        check=result["check"],
    )


# ── Year-End Close Endpoints ─────────────────────────────────────────────


@router.post("/year-end-close", response_model=schemas.YearEndCloseResponse, status_code=201)
def start_year_end_close(
    data: schemas.YearEndCloseStart, user_id: int = Query(0),
    db: Session = Depends(get_db),
):
    svc = YearEndCloseService(db)
    try:
        close = svc.start(data, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.YearEndCloseResponse(
        id=close.id, fiscal_year=close.fiscal_year, status=close.status,
        stages_completed=close.stages_completed or {},
        closing_period_id=close.closing_period_id,
        opening_period_id=close.opening_period_id,
        total_revenue=close.total_revenue or 0.0,
        total_expenses=close.total_expenses or 0.0,
        net_income=close.net_income or 0.0,
        started_at=close.started_at, completed_at=close.completed_at,
        created_at=close.created_at,
    )


@router.post("/year-end-close/{close_id}/stage", response_model=schemas.YearEndCloseResponse)
def complete_year_end_stage(
    close_id: int, data: schemas.YearEndStageComplete,
    user_id: int = Query(0), db: Session = Depends(get_db),
):
    svc = YearEndCloseService(db)
    try:
        close = svc.complete_stage(close_id, data.stage, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return schemas.YearEndCloseResponse(
        id=close.id, fiscal_year=close.fiscal_year, status=close.status,
        stages_completed=close.stages_completed or {},
        closing_period_id=close.closing_period_id,
        opening_period_id=close.opening_period_id,
        total_revenue=close.total_revenue or 0.0,
        total_expenses=close.total_expenses or 0.0,
        net_income=close.net_income or 0.0,
        started_at=close.started_at, completed_at=close.completed_at,
        created_at=close.created_at,
    )


@router.get("/year-end-close/{fiscal_year}", response_model=schemas.YearEndCloseResponse)
def get_year_end_close(fiscal_year: int, db: Session = Depends(get_db)):
    svc = YearEndCloseService(db)
    close = svc.get(fiscal_year)
    if not close:
        raise HTTPException(404, "Year-end close not found")
    return schemas.YearEndCloseResponse(
        id=close.id, fiscal_year=close.fiscal_year, status=close.status,
        stages_completed=close.stages_completed or {},
        closing_period_id=close.closing_period_id,
        opening_period_id=close.opening_period_id,
        total_revenue=close.total_revenue or 0.0,
        total_expenses=close.total_expenses or 0.0,
        net_income=close.net_income or 0.0,
        started_at=close.started_at, completed_at=close.completed_at,
        created_at=close.created_at,
    )


# ── Health Endpoint ──────────────────────────────────────────────────────


@router.get("/health", response_model=schemas.HealthResponse)
def health_check(db: Session = Depends(get_db)):
    svc = HealthService(db)
    result = svc.check()
    return schemas.HealthResponse(
        status=result["status"], module=result["module"],
        version=result["version"],
        metrics=[
            schemas.HealthMetric(
                name=m["name"], status=m["status"],
                value=m["value"], details=m.get("details"),
            )
            for m in result["metrics"]
        ],
    )
