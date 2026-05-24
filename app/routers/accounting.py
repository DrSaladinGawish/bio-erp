from __future__ import annotations

import logging
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token, create_refresh_token,
    get_current_user, require_user, verify_password,
)
from app.database import get_db
from app.models import COAAccount, COACategory, Branch, Currency, User
from app.template_engine import render_template
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["accounting"])





@router.post("/login")
async def login(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    from starlette.datastructures import FormData

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

    access_token = create_access_token({"sub": str(user.id), "username": user.username, "role": "admin" if user.is_superuser else "user"})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    resp = JSONResponse({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "full_name": user.full_name_en},
    })
    resp.set_cookie(key="access_token", value=access_token, httponly=True, max_age=900, samesite="lax")
    return resp


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
