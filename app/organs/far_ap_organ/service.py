from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session

from app.organs.far_ap_organ.models import (
    APVendor, APBill, APBillLine, APPayment, APCreditNote, APApprovalQueue,
    VendorStatus, BillStatus, PaymentMethod, CreditNoteStatus, AgingBucket,
)
from app.organs.far_ap_organ import schemas
from app.organs.far_gl_organ.service import JournalService as GLJournalService
from app.organs.far_gl_organ.schemas import JournalCreate as GLJournalCreate, JournalLineCreate as GLJournalLineCreate

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _generate_number(db: Session, prefix: str) -> str:
    from app.organs.far_ap_organ.models import APBill
    count = db.execute(select(func.count(APBill.id))).scalar() or 0
    return f"{prefix}-{_utcnow().year}-{count + 1:06d}"


class VendorService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: schemas.VendorCreate) -> APVendor:
        existing = self.db.execute(select(APVendor).where(APVendor.code == data.code)).scalar_one_or_none()
        if existing:
            raise ValueError(f"Vendor code '{data.code}' already exists")
        v = APVendor(**data.model_dump())
        self.db.add(v); self.db.commit(); self.db.refresh(v)
        return v

    def list(self, status: Optional[str] = None) -> List[APVendor]:
        q = select(APVendor).order_by(APVendor.code)
        if status:
            q = q.where(APVendor.status == status)
        return list(self.db.execute(q).scalars().all())

    def get(self, vid: int) -> Optional[APVendor]:
        return self.db.get(APVendor, vid)

    def update(self, vid: int, data: schemas.VendorUpdate) -> APVendor:
        v = self._get_or_raise(vid)
        for f, val in data.model_dump(exclude_unset=True).items():
            setattr(v, f, val)
        self.db.commit(); self.db.refresh(v)
        return v

    def _get_or_raise(self, vid: int) -> APVendor:
        v = self.db.get(APVendor, vid)
        if not v:
            raise ValueError(f"Vendor {vid} not found")
        return v


class BillService:
    def __init__(self, db: Session):
        self.db = db
        self._gl = GLJournalService(db)

    def create(self, data: schemas.BillCreate, user_id: int = 0) -> APBill:
        vendor = self.db.get(APVendor, data.vendor_id)
        if not vendor:
            raise ValueError(f"Vendor {data.vendor_id} not found")

        bill_num = _generate_number(self.db, "BILL")
        lines = []
        subtotal = tax_amount = total = 0.0
        for i, ld in enumerate(data.lines):
            net = ld.quantity * ld.unit_price * (1 - ld.discount_pct / 100)
            tax = net * ld.tax_rate / 100
            tot = net + tax
            subtotal += net; tax_amount += tax; total += tot
            lines.append(APBillLine(line_number=i + 1, description=ld.description,
                quantity=ld.quantity, unit_price=ld.unit_price, discount_pct=ld.discount_pct,
                tax_rate=ld.tax_rate, net_amount=round(net, 2), tax_amount=round(tax, 2),
                total_amount=round(tot, 2), gl_account_id=ld.gl_account_id))

        bill = APBill(bill_number=bill_num, vendor_id=data.vendor_id,
            bill_date=data.bill_date, due_date=data.due_date, status=BillStatus.DRAFT,
            subtotal=round(subtotal, 2), tax_amount=round(tax_amount, 2),
            total_amount=round(total, 2), balance_due=round(total, 2),
            currency_id=data.currency_id, exchange_rate=data.exchange_rate, notes=data.notes)
        self.db.add(bill); self.db.flush()
        for line in lines:
            line.bill_id = bill.id
            self.db.add(line)

        queue = APApprovalQueue(bill_id=bill.id, status="pending")
        self.db.add(queue)
        self.db.commit(); self.db.refresh(bill)
        return bill

    def approve(self, bill_id: int, data: schemas.ApproveAction, user_id: int = 0) -> APBill:
        bill = self._get_or_raise(bill_id)
        if bill.status != BillStatus.DRAFT:
            raise ValueError(f"Bill {bill.bill_number} is already {bill.status.value}")

        if data.approved:
            bill.status = BillStatus.APPROVED
            bill.approved_by = user_id
            bill.approved_at = _utcnow()

            period = self._get_open_period(bill.bill_date)
            expense_account = self._get_expense_account()
            ap_account = self._get_ap_account()
            tax_account = self._get_tax_account()

            lines = []
            lines.append(GLJournalLineCreate(account_id=expense_account.id, debit_amount=bill.subtotal, credit_amount=0.0,
                line_description=f"Expense: {bill.bill_number}"))
            if bill.tax_amount > 0:
                lines.append(GLJournalLineCreate(account_id=tax_account.id, debit_amount=bill.tax_amount, credit_amount=0.0,
                    line_description=f"VAT: {bill.bill_number}"))
            lines.append(GLJournalLineCreate(account_id=ap_account.id, debit_amount=0.0, credit_amount=bill.total_amount,
                line_description=f"AP: {bill.bill_number}"))

            journal = self._gl.create(GLJournalCreate(
                period_id=period.id, journal_date=bill.bill_date,
                description=f"AP Bill {bill.bill_number}", source="ap",
                reference_type="ap_bill", reference_id=bill.id, lines=lines,
            ), user_id)
            self._gl.post(journal.id, user_id)
            bill.journal_id = journal.id

        queue = self.db.execute(select(APApprovalQueue).where(
            APApprovalQueue.bill_id == bill_id)).scalar_one_or_none()
        if queue:
            queue.status = "approved" if data.approved else "rejected"
            queue.notes = data.notes

        self.db.commit(); self.db.refresh(bill)
        return bill

    def list(self, vendor_id: Optional[int] = None, status: Optional[str] = None,
             page: int = 1, page_size: int = 20) -> Tuple[List[APBill], int]:
        q = select(APBill).order_by(APBill.bill_date.desc(), APBill.id.desc())
        if vendor_id:
            q = q.where(APBill.vendor_id == vendor_id)
        if status:
            q = q.where(APBill.status == status)
        total = self.db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
        q = q.offset((page - 1) * page_size).limit(page_size)
        return list(self.db.execute(q).scalars().all()), total

    def get(self, bill_id: int) -> Optional[APBill]:
        return self.db.get(APBill, bill_id)

    def list_approval_queue(self) -> List[Dict[str, Any]]:
        items = list(self.db.execute(
            select(APApprovalQueue).where(APApprovalQueue.status == "pending")
            .order_by(APApprovalQueue.created_at)
        ).scalars().all())
        result = []
        for q in items:
            bill = self.db.get(APBill, q.bill_id)
            vendor = self.db.get(APVendor, bill.vendor_id) if bill else None
            result.append({"id": q.id, "bill_id": q.bill_id,
                "bill_number": bill.bill_number if bill else "?",
                "vendor_name": vendor.name_en if vendor else "?",
                "total_amount": bill.total_amount if bill else 0,
                "status": q.status, "created_at": q.created_at})
        return result

    def _get_or_raise(self, bill_id: int) -> APBill:
        bill = self.db.get(APBill, bill_id)
        if not bill:
            raise ValueError(f"Bill {bill_id} not found")
        return bill

    def _get_open_period(self, d: date):
        from app.organs.far_gl_organ.models import GLPeriod, PeriodStatus
        p = self.db.execute(select(GLPeriod).where(
            GLPeriod.start_date <= d, GLPeriod.end_date >= d,
            GLPeriod.status == PeriodStatus.OPEN,
        )).scalar_one_or_none()
        if not p:
            raise ValueError(f"No open period found for {d}")
        return p

    def _get_expense_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "6000")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.name_en.like("%Expense%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("Expense account not found in COA")
        return acct

    def _get_ap_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "2100")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.name_en.like("%Payable%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("AP account not found in COA")
        return acct

    def _get_tax_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "2200")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.name_en.like("%VAT%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("VAT account not found in COA")
        return acct


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self._gl = GLJournalService(db)

    def create(self, data: schemas.PaymentCreate, user_id: int = 0) -> APPayment:
        vendor = self.db.get(APVendor, data.vendor_id)
        if not vendor:
            raise ValueError(f"Vendor {data.vendor_id} not found")

        pmt_num = _generate_number(self.db, "AP-PMT")
        payment = APPayment(payment_number=pmt_num, vendor_id=data.vendor_id,
            bill_id=data.bill_id, payment_date=data.payment_date, amount=data.amount,
            payment_method=data.payment_method, reference=data.reference,
            currency_id=data.currency_id, exchange_rate=data.exchange_rate, notes=data.notes)
        self.db.add(payment); self.db.flush()

        if data.bill_id:
            bill = self.db.get(APBill, data.bill_id)
            if bill:
                new_paid = (bill.paid_amount or 0) + data.amount
                bill.paid_amount = round(new_paid, 2)
                bill.balance_due = round(max(0, bill.total_amount - new_paid), 2)
                if bill.balance_due <= 0.01:
                    bill.status = BillStatus.PAID
                else:
                    bill.status = BillStatus.PARTIALLY_PAID

        period = self._get_open_period(data.payment_date)
        ap_account = self._get_ap_account()
        bank_account = self._get_bank_account()

        lines = [
            GLJournalLineCreate(account_id=ap_account.id, debit_amount=data.amount, credit_amount=0.0,
                line_description=f"AP Payment: {pmt_num}"),
            GLJournalLineCreate(account_id=bank_account.id, debit_amount=0.0, credit_amount=data.amount,
                line_description=f"Bank: {pmt_num}"),
        ]
        journal = self._gl.create(GLJournalCreate(
            period_id=period.id, journal_date=data.payment_date,
            description=f"AP Payment {pmt_num}", source="ap",
            reference_type="ap_payment", reference_id=payment.id, lines=lines,
        ), user_id)
        self._gl.post(journal.id, user_id)
        payment.journal_id = journal.id
        self.db.commit(); self.db.refresh(payment)
        return payment

    def list(self, vendor_id: Optional[int] = None, page: int = 1, page_size: int = 20) -> Tuple[List[APPayment], int]:
        q = select(APPayment).order_by(APPayment.payment_date.desc(), APPayment.id.desc())
        if vendor_id:
            q = q.where(APPayment.vendor_id == vendor_id)
        total = self.db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
        q = q.offset((page - 1) * page_size).limit(page_size)
        return list(self.db.execute(q).scalars().all()), total

    def _get_open_period(self, d: date):
        from app.organs.far_gl_organ.models import GLPeriod, PeriodStatus
        p = self.db.execute(select(GLPeriod).where(
            GLPeriod.start_date <= d, GLPeriod.end_date >= d,
            GLPeriod.status == PeriodStatus.OPEN,
        )).scalar_one_or_none()
        if not p:
            raise ValueError(f"No open period found for {d}")
        return p

    def _get_ap_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "2100")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.name_en.like("%Payable%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("AP account not found in COA")
        return acct

    def _get_bank_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "1020")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.name_en.like("%Bank%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("Bank account not found in COA")
        return acct


class CreditNoteService:
    def __init__(self, db: Session):
        self.db = db
        self._gl = GLJournalService(db)

    def create(self, data: schemas.CreditNoteCreate, user_id: int = 0) -> APCreditNote:
        vendor = self.db.get(APVendor, data.vendor_id)
        if not vendor:
            raise ValueError(f"Vendor {data.vendor_id} not found")

        cn_num = _generate_number(self.db, "AP-CN")
        cn = APCreditNote(credit_note_number=cn_num, vendor_id=data.vendor_id,
            bill_id=data.bill_id, credit_date=data.credit_date, amount=data.amount,
            reason=data.reason, notes=data.notes)
        self.db.add(cn); self.db.flush()

        if data.bill_id:
            bill = self.db.get(APBill, data.bill_id)
            if bill:
                bill.balance_due = round(max(0, bill.balance_due - data.amount), 2)
                bill.paid_amount = round(max(0, bill.paid_amount - data.amount), 2)
                if bill.balance_due <= 0.01 and bill.paid_amount >= bill.total_amount - 0.01:
                    bill.status = BillStatus.CREDITED

        period = self._get_open_period(data.credit_date)
        ap_account = self._get_ap_account()
        expense_account = self._get_expense_account()

        lines = [
            GLJournalLineCreate(account_id=ap_account.id, debit_amount=data.amount, credit_amount=0.0,
                line_description=f"AP Credit: {cn_num}"),
            GLJournalLineCreate(account_id=expense_account.id, debit_amount=0.0, credit_amount=data.amount,
                line_description=f"Expense Credit: {cn_num}"),
        ]
        journal = self._gl.create(GLJournalCreate(
            period_id=period.id, journal_date=data.credit_date,
            description=f"AP Credit Note {cn_num}", source="ap",
            reference_type="ap_credit_note", reference_id=cn.id, lines=lines,
        ), user_id)
        self._gl.post(journal.id, user_id)
        cn.status = CreditNoteStatus.POSTED
        cn.journal_id = journal.id
        self.db.commit(); self.db.refresh(cn)
        return cn

    def list(self, vendor_id: Optional[int] = None) -> List[APCreditNote]:
        q = select(APCreditNote).order_by(APCreditNote.id.desc())
        if vendor_id:
            q = q.where(APCreditNote.vendor_id == vendor_id)
        return list(self.db.execute(q).scalars().all())

    def _get_open_period(self, d: date):
        from app.organs.far_gl_organ.models import GLPeriod, PeriodStatus
        return self.db.execute(select(GLPeriod).where(
            GLPeriod.start_date <= d, GLPeriod.end_date >= d,
            GLPeriod.status == PeriodStatus.OPEN,
        )).scalar_one_or_none()

    def _get_ap_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "2100")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.name_en.like("%Payable%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("AP account not found in COA")
        return acct

    def _get_expense_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "6000")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.name_en.like("%Expense%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("Expense account not found in COA")
        return acct


class AgingService:
    def __init__(self, db: Session):
        self.db = db

    def calculate(self, vid: int, as_of: Optional[date] = None) -> Dict[str, Any]:
        as_of = as_of or date.today()
        vendor = self.db.get(APVendor, vid)
        if not vendor:
            raise ValueError(f"Vendor {vid} not found")
        bills = list(self.db.execute(select(APBill).where(
            APBill.vendor_id == vid,
            APBill.status.in_([BillStatus.APPROVED, BillStatus.PARTIALLY_PAID]),
        )).scalars().all())
        buckets = {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "61_90": 0.0, "over_90": 0.0}
        for b in bills:
            bal = b.balance_due
            if bal <= 0:
                continue
            days_overdue = (as_of - b.due_date).days
            if days_overdue <= 0:
                buckets["current"] += bal
            elif days_overdue <= 30:
                buckets["1_30"] += bal
            elif days_overdue <= 60:
                buckets["31_60"] += bal
            elif days_overdue <= 90:
                buckets["61_90"] += bal
            else:
                buckets["over_90"] += bal
        total = sum(buckets.values())
        return {"vendor_id": vid, "vendor_name": vendor.name_en,
                "total_outstanding": round(total, 2), "buckets": buckets, "as_of_date": as_of}


class HealthService:
    def __init__(self, db: Session):
        self.db = db

    def check(self) -> Dict[str, Any]:
        return {"status": "healthy", "module": "far-ap", "version": "1.0.0",
            "vendors": self.db.execute(select(func.count(APVendor.id))).scalar() or 0,
            "bills": self.db.execute(select(func.count(APBill.id))).scalar() or 0,
            "payments": self.db.execute(select(func.count(APPayment.id))).scalar() or 0}
