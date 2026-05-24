from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import (
    create_access_token, create_refresh_token,
    get_current_user, require_user, verify_password,
)
from app.database import get_db
from app.middleware.auth import RequirePermission
from app.models import (
    COAAccount, COACategory, Branch, Currency, User,
    JVHeader, JVLine, CustomerInvoice, VendorInvoice,
    RCTHeader, PMTHeader,
)
from app.services.gl_posting import GLPostingService
from app.template_engine import render_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/accounting", tags=["Accounting"])


# ── Pydantic schemas (from ERP-PC) ──────────────────────────────────────


class AccountCreate(BaseModel):
    code: str
    name_en: str
    name_ar: Optional[str] = None
    category_id: int
    account_type: Optional[str] = None
    is_control_account: bool = False
    parent_id: Optional[int] = None
    opening_balance: float = 0.0
    opening_balance_date: Optional[str] = None


class AccountUpdate(BaseModel):
    code: Optional[str] = None
    name_en: Optional[str] = None
    name_ar: Optional[str] = None
    category_id: Optional[int] = None
    account_type: Optional[str] = None
    is_control_account: Optional[bool] = None
    parent_id: Optional[int] = None
    opening_balance: Optional[float] = None
    opening_balance_date: Optional[str] = None


# ── Auth (from ERP-PC) ──────────────────────────────────────────────────


@router.post("/login")
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    data = None
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
    elif "application/x-www-form-urlencoded" in content_type or "multipart" in content_type:
        form = await request.form()
        data = dict(form)

    if not data:
        return JSONResponse({"detail": "Invalid content type"}, status_code=400)

    username = data.get("username", "")
    password = data.get("password", "")

    if not username or not password:
        return JSONResponse({"detail": "Username and password required"}, status_code=400)

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        return JSONResponse({"detail": "Invalid credentials"}, status_code=401)

    access_token = create_access_token({
        "sub": str(user.id), "username": user.username,
        "role": "admin" if user.is_superuser else "user",
    })
    refresh_token = create_refresh_token({"sub": str(user.id)})

    resp = JSONResponse({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "full_name": user.full_name_en},
    })
    resp.set_cookie(key="access_token", value=access_token, httponly=True, max_age=900, samesite="lax")
    return resp


# ── HTMX Ledger UI (from ERP-PC) ────────────────────────────────────────


async def get_ledger_summary(db: AsyncSession):
    result = await db.execute(
        select(
            COAAccount.category_id,
            COACategory.name_en,
            func.count(COAAccount.id).label("account_count"),
            func.coalesce(func.sum(COAAccount.opening_balance), 0).label("total_balance"),
        )
        .join(COACategory, COAAccount.category_id == COACategory.id)
        .group_by(COAAccount.category_id, COACategory.name_en)
        .order_by(COACategory.name_en)
    )
    return result.all()


@router.get("/ledger-inquiry")
async def ledger_inquiry(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accounts_result = await db.execute(
        select(COAAccount).where(COAAccount.is_active == True).order_by(COAAccount.code)
    )
    accounts = accounts_result.scalars().all()

    categories_result = await db.execute(
        select(COACategory).order_by(COACategory.name_en)
    )
    categories = categories_result.scalars().all()

    branches_result = await db.execute(
        select(Branch).where(Branch.is_active == True).order_by(Branch.name_en)
    )
    branches = branches_result.scalars().all()

    currencies_result = await db.execute(
        select(Currency).order_by(Currency.code)
    )
    currencies = currencies_result.scalars().all()

    summary = await get_ledger_summary(db)

    return render_template("ledger.html", {
        "request": request,
        "accounts": accounts,
        "categories": categories,
        "branches": branches,
        "currencies": currencies,
        "summary": summary,
        "current_user": current_user,
    })


@router.get("/ledger-entries")
async def ledger_entries_table(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    account_id: int | None = Query(None),
    category_id: int | None = Query(None),
    branch_id: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=500),
):
    query = select(COAAccount).where(COAAccount.is_active == True)

    if account_id:
        query = query.where(COAAccount.id == account_id)
    if category_id:
        query = query.where(COAAccount.category_id == category_id)
    if search:
        like = f"%{search}%"
        query = query.where(
            (COAAccount.name_en.ilike(like)) | (COAAccount.code.ilike(like)) | (COAAccount.name_ar.ilike(like))
        )

    query = query.order_by(COAAccount.code)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    accounts = result.scalars().all()

    return render_template("ledger_table.html", {
        "request": request,
        "accounts": accounts,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "current_user": current_user,
    })


@router.post("/ledger-entries")
async def create_ledger_entry(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = COAAccount(
        code=payload.code,
        name_en=payload.name_en,
        name_ar=payload.name_ar,
        category_id=payload.category_id,
        account_type=payload.account_type,
        is_control_account=payload.is_control_account,
        parent_id=payload.parent_id,
        opening_balance=payload.opening_balance,
        opening_balance_date=payload.opening_balance_date,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return JSONResponse({
        "id": account.id,
        "code": account.code,
        "name_en": account.name_en,
    }, status_code=status.HTTP_201_CREATED)


@router.put("/ledger-entries/{entry_id}")
async def update_ledger_entry(
    entry_id: int,
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(COAAccount).where(COAAccount.id == entry_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return JSONResponse({
        "id": account.id,
        "code": account.code,
        "name_en": account.name_en,
    })


@router.delete("/ledger-entries/{entry_id}")
async def delete_ledger_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(COAAccount).where(COAAccount.id == entry_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    account.is_active = False
    await db.commit()
    return JSONResponse({"detail": "Account deactivated"})


# ── Financial endpoints (from USB) ──────────────────────────────────────


@router.get("/trial-balance")
async def trial_balance(
    as_of_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("accounting.read")),
):
    as_of = as_of_date or date.today()
    result = await db.execute(
        select(COAAccount)
        .options(selectinload(COAAccount.category))
        .where(COAAccount.is_active)
    )
    accounts = result.scalars().all()

    lines_result = await db.execute(
        select(JVLine)
        .join(JVHeader)
        .where(JVHeader.gl_posted, JVHeader.jv_date <= as_of)
    )
    lines = lines_result.scalars().all()

    balances = {}
    for line in lines:
        acct_id = line.gl_account_id
        if acct_id not in balances:
            balances[acct_id] = 0.0
        balances[acct_id] += line.debit_amount - line.credit_amount

    rows = []
    total_debit = 0.0
    total_credit = 0.0
    for acct in accounts:
        balance = balances.get(acct.id, 0.0) + acct.opening_balance
        dr = max(balance, 0)
        cr = max(-balance, 0)
        category_code = acct.category.code if acct.category else ""
        rows.append({
            "account_code": acct.code,
            "account_name": acct.name_en,
            "category_code": category_code,
            "account_type": acct.account_type,
            "debit": round(dr, 2),
            "credit": round(cr, 2),
        })
        total_debit += dr
        total_credit += cr

    return {
        "as_of_date": as_of.isoformat(),
        "rows": rows,
        "total_debit": round(total_debit, 2),
        "total_credit": round(total_credit, 2),
    }


@router.get("/general-ledger")
async def general_ledger(
    account_id: int | None = Query(None),
    account_code: str | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    limit: int = Query(200, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("accounting.read")),
):
    query = (
        select(
            JVLine,
            JVHeader.jv_number,
            JVHeader.jv_date,
            JVHeader.description.label("jv_description"),
        )
        .join(JVHeader)
        .where(JVHeader.gl_posted)
    )
    if account_id:
        query = query.where(JVLine.gl_account_id == account_id)
    if account_code:
        acct_result = await db.execute(
            select(COAAccount.id).where(COAAccount.code == account_code)
        )
        acct = acct_result.scalar_one_or_none()
        if not acct:
            raise HTTPException(404, detail=f"Account {account_code} not found")
        query = query.where(JVLine.gl_account_id == acct)
    if from_date:
        query = query.where(JVHeader.jv_date >= from_date)
    if to_date:
        query = query.where(JVHeader.jv_date <= to_date)

    query = query.order_by(JVHeader.jv_date.desc()).limit(limit)
    result = await db.execute(query)
    entries = result.all()

    return [
        {
            "jv_number": entry.jv_number,
            "jv_date": entry.jv_date,
            "description": entry.jv_description,
            "line_description": entry.JVLine.description,
            "gl_account_id": entry.JVLine.gl_account_id,
            "debit_amount": entry.JVLine.debit_amount,
            "credit_amount": entry.JVLine.credit_amount,
        }
        for entry in entries
    ]


@router.get("/account-balances")
async def account_balances(
    category_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("accounting.read")),
):
    query = select(COAAccount).where(COAAccount.is_active)
    if category_id:
        query = query.where(COAAccount.category_id == category_id)
    result = await db.execute(query.options(selectinload(COAAccount.category)))
    accounts = result.scalars().all()

    lines_result = await db.execute(
        select(JVLine).join(JVHeader).where(JVHeader.gl_posted)
    )
    lines = lines_result.scalars().all()

    totals = {}
    for line in lines:
        if line.gl_account_id not in totals:
            totals[line.gl_account_id] = 0.0
        totals[line.gl_account_id] += line.debit_amount - line.credit_amount

    return [
        {
            "id": a.id,
            "code": a.code,
            "name_en": a.name_en,
            "account_type": a.account_type,
            "category_code": a.category.code if a.category else None,
            "opening_balance": a.opening_balance,
            "net_movement": round(totals.get(a.id, 0.0), 2),
            "closing_balance": round(a.opening_balance + totals.get(a.id, 0.0), 2),
        }
        for a in accounts
    ]


@router.get("/income-statement")
async def income_statement(
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("accounting.read")),
):
    lines_result = await db.execute(
        select(JVLine, JVHeader.jv_date).join(JVHeader).where(JVHeader.gl_posted)
    )
    entries = lines_result.all()

    income_result = await db.execute(
        select(COAAccount)
        .join(COACategory)
        .where(
            COAAccount.is_active,
            COAAccount.account_type.in_(["Income", "Revenue"]),
        )
    )
    income_accounts = {a.id: a for a in income_result.scalars().all()}

    expense_result = await db.execute(
        select(COAAccount)
        .join(COACategory)
        .where(
            COAAccount.is_active,
            COAAccount.account_type.in_(["Expense", "Cost"]),
        )
    )
    expense_accounts = {a.id: a for a in expense_result.scalars().all()}

    income = {}
    expenses = {}
    for jv_line, jv_date in entries:
        amt = jv_line.credit_amount - jv_line.debit_amount
        if jv_line.gl_account_id in income_accounts:
            key = jv_line.gl_account_id
            income[key] = income.get(key, 0.0) + amt
        if jv_line.gl_account_id in expense_accounts:
            key = jv_line.gl_account_id
            expenses[key] = expenses.get(key, 0.0) + abs(amt)

    total_income = sum(income.values())
    total_expenses = sum(expenses.values())
    net_income = total_income - total_expenses

    return {
        "from_date": (from_date or date.min).isoformat(),
        "to_date": (to_date or date.today()).isoformat(),
        "income": [
            {
                "account_code": income_accounts[aid].code,
                "account_name": income_accounts[aid].name_en,
                "amount": round(amt, 2),
            }
            for aid, amt in income.items()
            if aid in income_accounts
        ],
        "total_income": round(total_income, 2),
        "expenses": [
            {
                "account_code": expense_accounts[aid].code,
                "account_name": expense_accounts[aid].name_en,
                "amount": round(amt, 2),
            }
            for aid, amt in expenses.items()
            if aid in expense_accounts
        ],
        "total_expenses": round(total_expenses, 2),
        "net_income": round(net_income, 2),
    }


@router.post("/gl-post/{transaction_type}/{transaction_id}")
async def trigger_gl_posting(
    transaction_type: str,
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(RequirePermission("accounting.post")),
):
    svc = GLPostingService(db)

    if transaction_type == "ar_invoice":
        result = await db.execute(
            select(CustomerInvoice).where(CustomerInvoice.id == transaction_id)
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise HTTPException(404, detail="AR invoice not found")
        jv = await svc.post_ar_invoice(invoice)
    elif transaction_type == "ap_invoice":
        result = await db.execute(
            select(VendorInvoice).where(VendorInvoice.id == transaction_id)
        )
        invoice = result.scalar_one_or_none()
        if not invoice:
            raise HTTPException(404, detail="AP invoice not found")
        jv = await svc.post_ap_invoice(invoice)
    elif transaction_type == "receipt":
        result = await db.execute(
            select(RCTHeader).where(RCTHeader.id == transaction_id)
        )
        receipt = result.scalar_one_or_none()
        if not receipt:
            raise HTTPException(404, detail="Receipt not found")
        jv = await svc.post_receipt(receipt)
    elif transaction_type == "payment":
        result = await db.execute(
            select(PMTHeader).where(PMTHeader.id == transaction_id)
        )
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(404, detail="Payment not found")
        jv = await svc.post_payment(payment)
    else:
        raise HTTPException(400, detail=f"Unknown transaction type: {transaction_type}")

    if not jv:
        raise HTTPException(
            400, detail="Transaction already GL-posted or accounts not configured"
        )

    await db.commit()
    return {"jv_id": jv.id, "jv_number": jv.jv_number, "status": "Posted"}
