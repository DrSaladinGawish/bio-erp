from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session

from app.organs.far_ar_organ.models import (
    ARCustomer, ARInvoice, ARInvoiceLine, ARPayment, ARCreditNote, ARAgingBucket,
    CustomerStatus, InvoiceStatus, PaymentMethod, CreditNoteStatus, AgingBucket,
)
from app.organs.far_ar_organ import schemas
from app.organs.far_gl_organ.service import JournalService as GLJournalService
from app.organs.far_gl_organ.schemas import JournalCreate as GLJournalCreate, JournalLineCreate as GLJournalLineCreate

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _generate_number(db: Session, prefix: str, table_attr: str) -> str:
    count = db.execute(select(func.count()).select_from(
        select(getattr(ARInvoice, table_attr) if table_attr == "invoice_number" else
               getattr(ARPayment, table_attr) if table_attr == "payment_number" else
               getattr(ARCreditNote, table_attr)).subquery()
    )).scalar() or 0
    return f"{prefix}-{_utcnow().year}-{count + 1:06d}"


class CustomerService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: schemas.CustomerCreate) -> ARCustomer:
        existing = self.db.execute(select(ARCustomer).where(ARCustomer.code == data.code)).scalar_one_or_none()
        if existing:
            raise ValueError(f"Customer code '{data.code}' already exists")
        cust = ARCustomer(**data.model_dump())
        self.db.add(cust); self.db.commit(); self.db.refresh(cust)
        return cust

    def list(self, status: Optional[str] = None) -> List[ARCustomer]:
        q = select(ARCustomer).order_by(ARCustomer.code)
        if status:
            q = q.where(ARCustomer.status == status)
        return list(self.db.execute(q).scalars().all())

    def get(self, cust_id: int) -> Optional[ARCustomer]:
        return self.db.get(ARCustomer, cust_id)

    def update(self, cust_id: int, data: schemas.CustomerUpdate) -> ARCustomer:
        cust = self._get_or_raise(cust_id)
        for f, v in data.model_dump(exclude_unset=True).items():
            setattr(cust, f, v)
        self.db.commit(); self.db.refresh(cust)
        return cust

    def check_credit(self, cust_id: int, amount: float) -> Dict[str, Any]:
        cust = self._get_or_raise(cust_id)
        available = cust.credit_limit - cust.credit_used
        return {"customer_id": cust_id, "customer_name": cust.name_en,
                "credit_limit": cust.credit_limit, "credit_used": cust.credit_used,
                "available": round(available, 2), "approved": available >= amount}

    def _get_or_raise(self, cust_id: int) -> ARCustomer:
        cust = self.db.get(ARCustomer, cust_id)
        if not cust:
            raise ValueError(f"Customer {cust_id} not found")
        return cust


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self._gl = GLJournalService(db)

    def create(self, data: schemas.InvoiceCreate, user_id: int = 0) -> ARInvoice:
        cust = self.db.get(ARCustomer, data.customer_id)
        if not cust:
            raise ValueError(f"Customer {data.customer_id} not found")
        if cust.status != CustomerStatus.ACTIVE:
            raise ValueError(f"Customer {cust.code} is {cust.status.value}")

        inv_num = _generate_number(self.db, "INV", "invoice_number")
        lines = []
        subtotal = tax_amount = total = 0.0
        for i, ld in enumerate(data.lines):
            net = ld.quantity * ld.unit_price * (1 - ld.discount_pct / 100)
            tax = net * ld.tax_rate / 100
            tot = net + tax
            subtotal += net; tax_amount += tax; total += tot
            lines.append(ARInvoiceLine(line_number=i + 1, description=ld.description,
                quantity=ld.quantity, unit_price=ld.unit_price, discount_pct=ld.discount_pct,
                tax_rate=ld.tax_rate, net_amount=round(net, 2), tax_amount=round(tax, 2),
                total_amount=round(tot, 2), gl_account_id=ld.gl_account_id))

        if cust.credit_limit > 0 and (cust.credit_used + total) > cust.credit_limit:
            raise ValueError(f"Credit limit exceeded: {cust.credit_used} + {total:.2f} > {cust.credit_limit}")

        invoice = ARInvoice(
            invoice_number=inv_num, customer_id=data.customer_id,
            invoice_date=data.invoice_date, due_date=data.due_date,
            status=InvoiceStatus.DRAFT, subtotal=round(subtotal, 2),
            tax_amount=round(tax_amount, 2), total_amount=round(total, 2),
            balance_due=round(total, 2), currency_id=data.currency_id,
            exchange_rate=data.exchange_rate, notes=data.notes,
        )
        self.db.add(invoice); self.db.flush()
        for line in lines:
            line.invoice_id = invoice.id
            self.db.add(line)
        self.db.commit(); self.db.refresh(invoice)
        return invoice

    def send(self, inv_id: int, user_id: int = 0) -> ARInvoice:
        inv = self._get_or_raise(inv_id)
        if inv.status != InvoiceStatus.DRAFT:
            raise ValueError(f"Invoice {inv.invoice_number} is already {inv.status.value}")
        cust = self.db.get(ARCustomer, inv.customer_id)
        period = self._get_open_period(inv.invoice_date)
        ar_account = self._get_ar_account()
        revenue_account = self._get_revenue_account()
        tax_account = self._get_tax_account()

        lines = []
        lines.append(GLJournalLineCreate(account_id=ar_account.id, debit_amount=inv.total_amount, credit_amount=0.0,
            line_description=f"AR: {inv.invoice_number}"))
        lines.append(GLJournalLineCreate(account_id=revenue_account.id, debit_amount=0.0, credit_amount=inv.subtotal,
            line_description=f"Revenue: {inv.invoice_number}"))
        if inv.tax_amount > 0:
            lines.append(GLJournalLineCreate(account_id=tax_account.id, debit_amount=0.0, credit_amount=inv.tax_amount,
                line_description=f"VAT: {inv.invoice_number}"))

        journal = self._gl.create(GLJournalCreate(
            period_id=period.id, journal_date=inv.invoice_date,
            description=f"AR Invoice {inv.invoice_number}", source="ar",
            reference_type="ar_invoice", reference_id=inv.id, lines=lines,
        ), user_id)
        self._gl.post(journal.id, user_id)

        inv.status = InvoiceStatus.SENT
        inv.journal_id = journal.id
        cust.credit_used = (cust.credit_used or 0) + inv.total_amount
        self.db.commit(); self.db.refresh(inv)
        return inv

    def list(self, customer_id: Optional[int] = None, status: Optional[str] = None,
             page: int = 1, page_size: int = 20) -> Tuple[List[ARInvoice], int]:
        q = select(ARInvoice).order_by(ARInvoice.invoice_date.desc(), ARInvoice.id.desc())
        if customer_id:
            q = q.where(ARInvoice.customer_id == customer_id)
        if status:
            q = q.where(ARInvoice.status == status)
        total = self.db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
        q = q.offset((page - 1) * page_size).limit(page_size)
        return list(self.db.execute(q).scalars().all()), total

    def get(self, inv_id: int) -> Optional[ARInvoice]:
        return self.db.get(ARInvoice, inv_id)

    def _get_or_raise(self, inv_id: int) -> ARInvoice:
        inv = self.db.get(ARInvoice, inv_id)
        if not inv:
            raise ValueError(f"Invoice {inv_id} not found")
        return inv

    def _get_open_period(self, d: date):
        from app.organs.far_gl_organ.models import GLPeriod, PeriodStatus
        period = self.db.execute(select(GLPeriod).where(
            GLPeriod.start_date <= d, GLPeriod.end_date >= d,
            GLPeriod.status == PeriodStatus.OPEN,
        )).scalar_one_or_none()
        if not period:
            raise ValueError(f"No open period found for {d}")
        return period

    def _get_ar_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "1100")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.account_type == "asset",
                GLAccount.name_en.like("%Receivable%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("AR account not found in COA")
        return acct

    def _get_revenue_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "4100")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.account_type == "revenue")).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("Revenue account not found in COA")
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

    def create(self, data: schemas.PaymentCreate, user_id: int = 0) -> ARPayment:
        cust = self.db.get(ARCustomer, data.customer_id)
        if not cust:
            raise ValueError(f"Customer {data.customer_id} not found")

        pmt_num = _generate_number(self.db, "PMT", "payment_number")
        payment = ARPayment(
            payment_number=pmt_num, customer_id=data.customer_id,
            invoice_id=data.invoice_id, payment_date=data.payment_date,
            amount=data.amount, payment_method=data.payment_method,
            reference=data.reference, currency_id=data.currency_id,
            exchange_rate=data.exchange_rate, notes=data.notes,
        )
        self.db.add(payment); self.db.flush()

        inv: Optional[ARInvoice] = None
        if data.invoice_id:
            inv = self.db.get(ARInvoice, data.invoice_id)
            if inv:
                new_paid = (inv.paid_amount or 0) + data.amount
                inv.paid_amount = round(new_paid, 2)
                inv.balance_due = round(max(0, inv.total_amount - new_paid), 2)
                if inv.balance_due <= 0.01:
                    inv.status = InvoiceStatus.PAID
                else:
                    inv.status = InvoiceStatus.PARTIALLY_PAID
                cust.credit_used = round(max(0, (cust.credit_used or 0) - data.amount), 2)

        period = self._get_open_period(data.payment_date)
        bank_account = self._get_bank_account()
        ar_account = self._get_ar_account()

        lines = []
        lines.append(GLJournalLineCreate(account_id=bank_account.id, debit_amount=data.amount, credit_amount=0.0,
            line_description=f"Payment: {pmt_num}"))
        lines.append(GLJournalLineCreate(account_id=ar_account.id, debit_amount=0.0, credit_amount=data.amount,
            line_description=f"AR Payment: {pmt_num}"))

        journal = self._gl.create(GLJournalCreate(
            period_id=period.id, journal_date=data.payment_date,
            description=f"AR Payment {pmt_num}", source="ar",
            reference_type="ar_payment", reference_id=payment.id, lines=lines,
        ), user_id)
        self._gl.post(journal.id, user_id)

        payment.journal_id = journal.id
        self.db.commit(); self.db.refresh(payment)
        return payment

    def list(self, customer_id: Optional[int] = None, page: int = 1, page_size: int = 20) -> Tuple[List[ARPayment], int]:
        q = select(ARPayment).order_by(ARPayment.payment_date.desc(), ARPayment.id.desc())
        if customer_id:
            q = q.where(ARPayment.customer_id == customer_id)
        total = self.db.execute(select(func.count()).select_from(q.subquery())).scalar() or 0
        q = q.offset((page - 1) * page_size).limit(page_size)
        return list(self.db.execute(q).scalars().all()), total

    def _get_open_period(self, d: date):
        from app.organs.far_gl_organ.models import GLPeriod, PeriodStatus
        period = self.db.execute(select(GLPeriod).where(
            GLPeriod.start_date <= d, GLPeriod.end_date >= d,
            GLPeriod.status == PeriodStatus.OPEN,
        )).scalar_one_or_none()
        if not period:
            raise ValueError(f"No open period found for {d}")
        return period

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

    def _get_ar_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "1100")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.name_en.like("%Receivable%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("AR account not found in COA")
        return acct


class CreditNoteService:
    def __init__(self, db: Session):
        self.db = db
        self._gl = GLJournalService(db)

    def create(self, data: schemas.CreditNoteCreate, user_id: int = 0) -> ARCreditNote:
        cust = self.db.get(ARCustomer, data.customer_id)
        if not cust:
            raise ValueError(f"Customer {data.customer_id} not found")

        cn_num = _generate_number(self.db, "CN", "credit_note_number")
        cn = ARCreditNote(
            credit_note_number=cn_num, customer_id=data.customer_id,
            invoice_id=data.invoice_id, credit_date=data.credit_date,
            amount=data.amount, reason=data.reason, notes=data.notes,
        )
        self.db.add(cn); self.db.flush()

        if data.invoice_id:
            inv = self.db.get(ARInvoice, data.invoice_id)
            if inv:
                inv.balance_due = round(max(0, inv.balance_due - data.amount), 2)
                inv.paid_amount = round(max(0, inv.paid_amount - data.amount), 2)
                if inv.balance_due <= 0.01 and inv.paid_amount >= inv.total_amount - 0.01:
                    inv.status = InvoiceStatus.CREDITED
                cust.credit_used = round(max(0, (cust.credit_used or 0) - data.amount), 2)

        period = self._get_open_period(data.credit_date)
        ar_account = self._get_ar_account()
        revenue_account = self._get_revenue_account()

        lines = [
            GLJournalLineCreate(account_id=revenue_account.id, debit_amount=data.amount, credit_amount=0.0,
                line_description=f"Credit Note: {cn_num}"),
            GLJournalLineCreate(account_id=ar_account.id, debit_amount=0.0, credit_amount=data.amount,
                line_description=f"AR Credit: {cn_num}"),
        ]

        journal = self._gl.create(GLJournalCreate(
            period_id=period.id, journal_date=data.credit_date,
            description=f"Credit Note {cn_num}", source="ar",
            reference_type="ar_credit_note", reference_id=cn.id, lines=lines,
        ), user_id)
        self._gl.post(journal.id, user_id)

        cn.status = CreditNoteStatus.POSTED
        cn.journal_id = journal.id
        self.db.commit(); self.db.refresh(cn)
        return cn

    def list(self, customer_id: Optional[int] = None) -> List[ARCreditNote]:
        q = select(ARCreditNote).order_by(ARCreditNote.id.desc())
        if customer_id:
            q = q.where(ARCreditNote.customer_id == customer_id)
        return list(self.db.execute(q).scalars().all())

    def _get_open_period(self, d: date):
        from app.organs.far_gl_organ.models import GLPeriod, PeriodStatus
        return self.db.execute(select(GLPeriod).where(
            GLPeriod.start_date <= d, GLPeriod.end_date >= d,
            GLPeriod.status == PeriodStatus.OPEN,
        )).scalar_one_or_none()

    def _get_ar_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "1100")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.name_en.like("%Receivable%"))).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("AR account not found in COA")
        return acct

    def _get_revenue_account(self):
        from app.organs.far_gl_organ.models import GLAccount
        acct = self.db.execute(select(GLAccount).where(GLAccount.code == "4100")).scalar_one_or_none()
        if not acct:
            acct = self.db.execute(select(GLAccount).where(GLAccount.account_type == "revenue")).first()
            if acct:
                acct = acct[0]
        if not acct:
            raise ValueError("Revenue account not found in COA")
        return acct


class AgingService:
    def __init__(self, db: Session):
        self.db = db

    def calculate(self, cust_id: int, as_of: Optional[date] = None) -> Dict[str, Any]:
        as_of = as_of or date.today()
        cust = self.db.get(ARCustomer, cust_id)
        if not cust:
            raise ValueError(f"Customer {cust_id} not found")

        invoices = list(self.db.execute(
            select(ARInvoice).where(
                ARInvoice.customer_id == cust_id,
                ARInvoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE]),
            )
        ).scalars().all())

        buckets = {"current": 0.0, "1_30": 0.0, "31_60": 0.0, "61_90": 0.0, "over_90": 0.0}
        for inv in invoices:
            bal = inv.balance_due
            if bal <= 0:
                continue
            days_overdue = (as_of - inv.due_date).days
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
        return {"customer_id": cust_id, "customer_name": cust.name_en,
                "total_outstanding": round(total, 2), "buckets": buckets, "as_of_date": as_of}

    def get_overdue(self, days: int = 1) -> List[Dict[str, Any]]:
        cutoff = date.today() - timedelta(days=days)
        overdue_invoices = list(self.db.execute(
            select(ARInvoice).where(
                ARInvoice.due_date < cutoff,
                ARInvoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID]),
                ARInvoice.balance_due > 0,
            )
        ).scalars().all())
        result = []
        for inv in overdue_invoices:
            result.append({"invoice_id": inv.id, "invoice_number": inv.invoice_number,
                "customer_id": inv.customer_id, "amount": inv.balance_due,
                "due_date": inv.due_date.isoformat(), "days_overdue": (date.today() - inv.due_date).days})
        return result


class StatementService:
    def __init__(self, db: Session):
        self.db = db

    def generate(self, cust_id: int, period_start: date, period_end: date) -> Dict[str, Any]:
        cust = self.db.get(ARCustomer, cust_id)
        if not cust:
            raise ValueError(f"Customer {cust_id} not found")

        invoices = list(self.db.execute(
            select(ARInvoice).where(
                ARInvoice.customer_id == cust_id,
                ARInvoice.invoice_date <= period_end,
            ).order_by(ARInvoice.invoice_date)
        ).scalars().all())

        payments = list(self.db.execute(
            select(ARPayment).where(
                ARPayment.customer_id == cust_id,
                ARPayment.payment_date <= period_end,
            ).order_by(ARPayment.payment_date)
        ).scalars().all())

        lines = []
        running = 0.0
        for inv in invoices:
            if inv.invoice_date >= period_start:
                running += inv.total_amount
                lines.append(schemas.StatementLine(
                    date=inv.invoice_date, description=f"Invoice {inv.invoice_number}",
                    reference=inv.invoice_number, debit=inv.total_amount, credit=0.0, balance=round(running, 2)))

        for pmt in payments:
            if pmt.payment_date >= period_start:
                running -= pmt.amount
                lines.append(schemas.StatementLine(
                    date=pmt.payment_date, description=f"Payment {pmt.payment_number}",
                    reference=pmt.payment_number, debit=0.0, credit=pmt.amount, balance=round(running, 2)))

        lines.sort(key=lambda x: x.date)
        opening = running - sum(l.debit - l.credit for l in lines)
        return {"customer_id": cust_id, "customer_name": cust.name_en,
                "period_start": period_start, "period_end": period_end,
                "opening_balance": round(opening, 2), "closing_balance": round(running, 2), "lines": lines}


class HealthService:
    def __init__(self, db: Session):
        self.db = db

    def check(self) -> Dict[str, Any]:
        customers = self.db.execute(select(func.count(ARCustomer.id))).scalar() or 0
        invoices = self.db.execute(select(func.count(ARInvoice.id))).scalar() or 0
        payments = self.db.execute(select(func.count(ARPayment.id))).scalar() or 0
        return {"status": "healthy", "module": "far-ar", "version": "1.0.0",
                "customers": customers, "invoices": invoices, "payments": payments}
