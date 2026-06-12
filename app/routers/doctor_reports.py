from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ihe_models import ChartOfAccounts, JournalVoucher, JournalVoucherLine

router = APIRouter(prefix="/api/v1/doctor", tags=["Doctor Reports"])


async def _get_patient_count(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(ChartOfAccounts.AccountCode)))
    return result.scalar() or 0


@router.get("/health")
async def doctor_health(db: AsyncSession = Depends(get_db)):
    account_count = await _get_patient_count(db)
    return {
        "status": "healthy",
        "patients": [
            {
                "id": "ih-erp",
                "name": "IncentiveHouse ERP",
                "status": "connected",
                "accounts": account_count,
                "database": "IHE_ERP",
            }
        ],
        "report_types": [
            "consolidated-pl", "patient-health",
            "cross-patient-compare", "system-wide-audit",
            "trial-balance", "profit-loss", "balance-sheet", "cash-flow",
        ],
    }


@router.get("/reports/trial-balance")
async def doctor_trial_balance(
    as_of_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    target = as_of_date or date.today()
    stmt = (
        select(
            ChartOfAccounts.AccountCode,
            ChartOfAccounts.AccountName,
            ChartOfAccounts.AccountType,
            func.coalesce(func.sum(JournalVoucherLine.DebitAmount), 0).label("total_debit"),
            func.coalesce(func.sum(JournalVoucherLine.CreditAmount), 0).label("total_credit"),
        )
        .select_from(ChartOfAccounts)
        .outerjoin(
            JournalVoucherLine,
            ChartOfAccounts.AccountCode == JournalVoucherLine.AccountCode,
        )
        .outerjoin(
            JournalVoucher,
            and_(
                JournalVoucher.JVNumber == JournalVoucherLine.JVNumber,
                JournalVoucher.JVDate <= target,
            ),
        )
        .group_by(ChartOfAccounts.AccountCode, ChartOfAccounts.AccountName, ChartOfAccounts.AccountType)
        .order_by(ChartOfAccounts.AccountCode)
    )
    rows = await db.execute(stmt)
    accounts = []
    total_dr = Decimal("0")
    total_cr = Decimal("0")
    for row in rows:
        dr = Decimal(str(row.total_debit or 0))
        cr = Decimal(str(row.total_credit or 0))
        total_dr += dr
        total_cr += cr
        accounts.append({
            "account_code": row.AccountCode,
            "account_name": row.AccountName,
            "account_type": row.AccountType,
            "debit": float(dr),
            "credit": float(cr),
            "balance": float(dr - cr),
        })
    return {
        "patient": "ih-erp",
        "as_of_date": target.isoformat(),
        "accounts": accounts,
        "total_debit": float(total_dr),
        "total_credit": float(total_cr),
    }


@router.get("/reports/profit-loss")
async def doctor_profit_loss(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    revenue_types = ["Revenue", "Income"]
    expense_types = ["Expense", "Cost of Goods Sold", "COGS"]

    rev_stmt = (
        select(
            ChartOfAccounts.AccountCode, ChartOfAccounts.AccountName,
            (func.coalesce(func.sum(JournalVoucherLine.CreditAmount), 0)
             - func.coalesce(func.sum(JournalVoucherLine.DebitAmount), 0)).label("amount"),
        )
        .select_from(ChartOfAccounts)
        .outerjoin(JournalVoucherLine, ChartOfAccounts.AccountCode == JournalVoucherLine.AccountCode)
        .outerjoin(JournalVoucher, and_(
            JournalVoucher.JVNumber == JournalVoucherLine.JVNumber,
            JournalVoucher.JVDate.between(from_date, to_date),
        ))
        .where(ChartOfAccounts.AccountType.in_(revenue_types))
        .group_by(ChartOfAccounts.AccountCode, ChartOfAccounts.AccountName)
        .order_by(ChartOfAccounts.AccountCode)
    )
    exp_stmt = (
        select(
            ChartOfAccounts.AccountCode, ChartOfAccounts.AccountName,
            (func.coalesce(func.sum(JournalVoucherLine.DebitAmount), 0)
             - func.coalesce(func.sum(JournalVoucherLine.CreditAmount), 0)).label("amount"),
        )
        .select_from(ChartOfAccounts)
        .outerjoin(JournalVoucherLine, ChartOfAccounts.AccountCode == JournalVoucherLine.AccountCode)
        .outerjoin(JournalVoucher, and_(
            JournalVoucher.JVNumber == JournalVoucherLine.JVNumber,
            JournalVoucher.JVDate.between(from_date, to_date),
        ))
        .where(ChartOfAccounts.AccountType.in_(expense_types))
        .group_by(ChartOfAccounts.AccountCode, ChartOfAccounts.AccountName)
        .order_by(ChartOfAccounts.AccountCode)
    )

    revenues = await db.execute(rev_stmt)
    expenses = await db.execute(exp_stmt)

    rev_items = []
    total_rev = Decimal("0")
    for r in revenues:
        amt = Decimal(str(r.amount or 0))
        rev_items.append({"account_code": r.AccountCode, "account_name": r.AccountName, "amount": float(amt)})
        total_rev += amt

    exp_items = []
    total_exp = Decimal("0")
    for e in expenses:
        amt = Decimal(str(e.amount or 0))
        exp_items.append({"account_code": e.AccountCode, "account_name": e.AccountName, "amount": float(amt)})
        total_exp += amt

    net_income = float(total_rev - total_exp)
    return {
        "patient": "ih-erp",
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "revenues": rev_items, "total_revenue": float(total_rev),
        "expenses": exp_items, "total_expense": float(total_exp),
        "net_income": net_income,
    }


@router.get("/reports/balance-sheet")
async def doctor_balance_sheet(
    as_of_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    target = as_of_date or date.today()
    asset_types = ["Asset", "Current Asset", "Fixed Asset", "Non-Current Asset"]
    liability_types = ["Liability", "Current Liability", "Non-Current Liability"]
    equity_types = ["Equity", "Capital", "Retained Earnings"]

    stmt = (
        select(
            ChartOfAccounts.AccountType, ChartOfAccounts.AccountCode, ChartOfAccounts.AccountName,
            func.coalesce(func.sum(JournalVoucherLine.DebitAmount), 0).label("total_debit"),
            func.coalesce(func.sum(JournalVoucherLine.CreditAmount), 0).label("total_credit"),
        )
        .select_from(ChartOfAccounts)
        .outerjoin(JournalVoucherLine, ChartOfAccounts.AccountCode == JournalVoucherLine.AccountCode)
        .outerjoin(JournalVoucher, and_(
            JournalVoucher.JVNumber == JournalVoucherLine.JVNumber,
            JournalVoucher.JVDate <= target,
        ))
        .group_by(ChartOfAccounts.AccountType, ChartOfAccounts.AccountCode, ChartOfAccounts.AccountName)
        .order_by(ChartOfAccounts.AccountType, ChartOfAccounts.AccountCode)
    )
    rows = await db.execute(stmt)

    assets, liabilities, equity = [], [], []
    total_assets = total_liabilities = total_equity = Decimal("0")

    for row in rows:
        bal = Decimal(str(row.total_debit or 0)) - Decimal(str(row.total_credit or 0))
        item = {"account_code": row.AccountCode, "account_name": row.AccountName, "balance": float(bal)}
        if row.AccountType in asset_types:
            assets.append(item)
            total_assets += bal if bal >= 0 else Decimal("0")
        elif row.AccountType in liability_types:
            liabilities.append(item)
            total_liabilities += abs(bal) if bal < 0 else bal
        elif row.AccountType in equity_types:
            equity.append(item)
            total_equity += bal

    return {
        "patient": "ih-erp",
        "as_of_date": target.isoformat(),
        "assets": assets, "total_assets": float(total_assets),
        "liabilities": liabilities, "total_liabilities": float(total_liabilities),
        "equity": equity, "total_equity": float(total_equity),
    }


@router.get("/reports/cash-flow")
async def doctor_cash_flow(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    cash_stmt = select(ChartOfAccounts).where(
        ChartOfAccounts.AccountType.in_(["Current Asset", "Asset"]),
        and_(
            ChartOfAccounts.AccountName.ilike("%cash%"),
            ChartOfAccounts.AccountName.ilike("%bank%"),
        ),
    )
    cash_accounts = (await db.execute(cash_stmt)).scalars().all()
    if not cash_accounts:
        cash_stmt = select(ChartOfAccounts).where(
            ChartOfAccounts.AccountType.in_(["Current Asset", "Asset"]),
        )
        cash_accounts = (await db.execute(cash_stmt)).scalars().all()
    cash_codes = [c.AccountCode for c in cash_accounts]

    lines_stmt = (
        select(
            JournalVoucher.JVDate, JournalVoucher.Narration,
            JournalVoucherLine.AccountCode,
            JournalVoucherLine.DebitAmount, JournalVoucherLine.CreditAmount,
        )
        .select_from(JournalVoucherLine)
        .join(JournalVoucher, JournalVoucher.JVNumber == JournalVoucherLine.JVNumber)
        .where(
            JournalVoucherLine.AccountCode.in_(cash_codes),
            JournalVoucher.JVDate.between(from_date, to_date),
        )
        .order_by(JournalVoucher.JVDate)
    )
    rows = await db.execute(lines_stmt)

    operating = []
    net_operating = Decimal("0")
    for row in rows:
        net = Decimal(str(row.CreditAmount or 0)) - Decimal(str(row.DebitAmount or 0))
        operating.append({
            "date": row.JVDate.isoformat() if row.JVDate else "",
            "narration": row.Narration or "",
            "amount": float(net),
        })
        net_operating += net

    return {
        "patient": "ih-erp",
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "cash_accounts": [{"code": c.AccountCode, "name": c.AccountName} for c in cash_accounts],
        "operating": operating, "net_operating": float(net_operating),
        "investing": [], "net_investing": 0.0,
        "financing": [], "net_financing": 0.0,
        "net_change": float(net_operating),
    }


@router.get("/reports/consolidated-pl")
async def consolidated_pl(
    from_date: date = Query(...),
    to_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    pl = await doctor_profit_loss(from_date, to_date, db)
    return {
        "period": f"{from_date} to {to_date}",
        "patients": [pl],
        "consolidated": {
            "total_revenue": pl["total_revenue"],
            "total_expense": pl["total_expense"],
            "net_income": pl["net_income"],
        },
    }


@router.get("/reports/system-wide-audit")
async def system_wide_audit(db: AsyncSession = Depends(get_db)):
    account_count = await _get_patient_count(db)
    jv_count = (await db.execute(select(func.count(JournalVoucher.JVNumber)))).scalar() or 0
    return {
        "patients": [{"id": "ih-erp", "name": "IncentiveHouse ERP"}],
        "total_accounts": account_count,
        "total_transactions": jv_count,
        "audit_date": date.today().isoformat(),
    }
