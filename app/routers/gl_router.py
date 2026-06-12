from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.ihe_models import ChartOfAccounts, Employee, JournalVoucher

router = APIRouter(prefix="/api/v1/gl", tags=["General Ledger"])


class AccountOut(BaseModel):
    AccountCode: str
    AccountName: str
    AccountType: str
    ParentAccount: Optional[str] = None
    IsControlAccount: bool = False
    CurrencyCode: Optional[str] = None


class EmployeeOut(BaseModel):
    EmployeeCode: str
    EmployeeName: str
    EmployeeType: str
    PostingAccount: Optional[str] = None
    ExpenseAccount: Optional[str] = None
    IsActive: bool = True


class EmployeeCreate(BaseModel):
    EmployeeCode: str
    EmployeeName: str
    EmployeeType: str = "Staff"
    PostingAccount: Optional[str] = None
    ExpenseAccount: Optional[str] = None
    IsActive: bool = True


class VoucherOut(BaseModel):
    JVNumber: str
    JVDate: Optional[str] = None
    Narration: Optional[str] = None
    TotalDebit: Optional[float] = None
    TotalCredit: Optional[float] = None


class VoucherCreate(BaseModel):
    JVNumber: str
    JVDate: str
    Narration: Optional[str] = None
    TotalDebit: Optional[float] = None
    TotalCredit: Optional[float] = None


# -- Accounts --


@router.get("/accounts", response_model=list[AccountOut])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChartOfAccounts).order_by(ChartOfAccounts.AccountCode)
    )
    return result.scalars().all()


@router.get("/accounts/{account_code}", response_model=AccountOut)
async def get_account(account_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ChartOfAccounts).where(ChartOfAccounts.AccountCode == account_code)
    )
    acct = result.scalar_one_or_none()
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    return acct


# -- Employees --


@router.get("/employees", response_model=list[EmployeeOut])
async def list_employees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee).order_by(Employee.EmployeeCode))
    return result.scalars().all()


@router.post("/employees", response_model=EmployeeOut, status_code=201)
async def create_employee(payload: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    emp = Employee(**payload.model_dump())
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp


@router.get("/employees/{emp_code}", response_model=EmployeeOut)
async def get_employee(emp_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee).where(Employee.EmployeeCode == emp_code))
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return emp


@router.put("/employees/{emp_code}", response_model=EmployeeOut)
async def update_employee(
    emp_code: str, payload: EmployeeCreate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Employee).where(Employee.EmployeeCode == emp_code))
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    for key, val in payload.model_dump().items():
        setattr(emp, key, val)
    await db.commit()
    await db.refresh(emp)
    return emp


@router.delete("/employees/{emp_code}", status_code=204)
async def delete_employee(emp_code: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee).where(Employee.EmployeeCode == emp_code))
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    await db.delete(emp)
    await db.commit()


# -- Vouchers --


@router.get("/vouchers", response_model=list[VoucherOut])
async def list_vouchers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(JournalVoucher)
        .order_by(JournalVoucher.JVNumber)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/vouchers", response_model=VoucherOut, status_code=201)
async def create_voucher(payload: VoucherCreate, db: AsyncSession = Depends(get_db)):
    jv = JournalVoucher(**payload.model_dump())
    db.add(jv)
    await db.commit()
    await db.refresh(jv)
    return jv


@router.get("/vouchers/{jv_number}", response_model=VoucherOut)
async def get_voucher(jv_number: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(JournalVoucher).where(JournalVoucher.JVNumber == jv_number)
    )
    jv = result.scalar_one_or_none()
    if not jv:
        raise HTTPException(status_code=404, detail="Voucher not found")
    return jv
