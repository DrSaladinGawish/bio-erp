from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.coa import COAAccount
from app.models.finance import (
    JVHeader,
    JVLine,
    CustomerInvoice,
    VendorInvoice,
    RCTHeader,
    PMTHeader,
)
from app.services.serial_number import SerialNumberService


class GLPostingService:
    """Creates double-entry JV entries for financial transactions."""

    # Default account codes for standard posting (configurable)
    DEFAULT_ACCOUNTS = {
        "accounts_receivable": "1100",
        "accounts_payable": "2100",
        "revenue": "4000",
        "cost_of_sales": "5000",
        "cash": "1000",
        "bank": "1100",
        "vat_output": "2200",
        "vat_input": "1200",
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self._account_cache: dict[str, int | None] = {}

    async def _resolve_account(
        self, key: str, fallback_code: str | None = None
    ) -> int | None:
        code = self.DEFAULT_ACCOUNTS.get(key, fallback_code)
        if not code:
            return None
        if key in self._account_cache:
            return self._account_cache[key]
        result = await self.db.execute(
            select(COAAccount).where(COAAccount.code == code, COAAccount.is_active)
        )
        account = result.scalar_one_or_none()
        self._account_cache[key] = account.id if account else None
        return self._account_cache[key]

    async def post_ar_invoice(self, invoice: CustomerInvoice) -> JVHeader | None:
        if invoice.gl_posted:
            return None
        ar_acct = await self._resolve_account("accounts_receivable")
        rev_acct = await self._resolve_account("revenue")
        vat_acct = await self._resolve_account("vat_output")
        if not all([ar_acct, rev_acct]):
            return None

        sn = SerialNumberService(self.db)
        jv_number = await sn.generate("JV", JVHeader)

        jv = JVHeader(
            jv_number=jv_number,
            jv_date=invoice.invoice_date,
            reference=f"AR Invoice {invoice.invoice_number}",
            description=f"Auto-posting for invoice {invoice.invoice_number}",
            event_id=invoice.event_id,
            total_debit=invoice.total_amount,
            total_credit=invoice.total_amount,
            status="Posted",
            gl_posted=True,
            gl_posted_at=datetime.utcnow(),
            gl_period=invoice.invoice_date.strftime("%Y-%m"),
            created_by=invoice.created_by,
        )
        self.db.add(jv)
        await self.db.flush()

        line_no = 1
        self.db.add(
            JVLine(
                jv_id=jv.id,
                line_number=line_no,
                gl_account_id=ar_acct,
                debit_amount=invoice.total_amount,
                credit_amount=0.0,
                description=f"AR - {invoice.invoice_number}",
                event_id=invoice.event_id,
            )
        )
        line_no += 1
        self.db.add(
            JVLine(
                jv_id=jv.id,
                line_number=line_no,
                gl_account_id=rev_acct,
                debit_amount=0.0,
                credit_amount=invoice.subtotal,
                description=f"Revenue - {invoice.invoice_number}",
                event_id=invoice.event_id,
            )
        )
        if invoice.tax_amount > 0 and vat_acct:
            line_no += 1
            self.db.add(
                JVLine(
                    jv_id=jv.id,
                    line_number=line_no,
                    gl_account_id=vat_acct,
                    debit_amount=0.0,
                    credit_amount=invoice.tax_amount,
                    description=f"VAT Output - {invoice.invoice_number}",
                    event_id=invoice.event_id,
                )
            )

        invoice.gl_posted = True
        invoice.gl_posted_at = datetime.utcnow()
        invoice.gl_posted_by = invoice.created_by
        return jv

    async def post_ap_invoice(self, invoice: VendorInvoice) -> JVHeader | None:
        if invoice.gl_posted:
            return None
        ap_acct = await self._resolve_account("accounts_payable")
        cos_acct = await self._resolve_account("cost_of_sales")
        vat_acct = await self._resolve_account("vat_input")
        if not all([ap_acct, cos_acct]):
            return None

        sn = SerialNumberService(self.db)
        jv_number = await sn.generate("JV", JVHeader)

        jv = JVHeader(
            jv_number=jv_number,
            jv_date=invoice.invoice_date,
            reference=f"AP Invoice {invoice.invoice_number}",
            description=f"Auto-posting for vendor invoice {invoice.invoice_number}",
            event_id=invoice.event_id,
            total_debit=invoice.total_amount,
            total_credit=invoice.total_amount,
            status="Posted",
            gl_posted=True,
            gl_posted_at=datetime.utcnow(),
            gl_period=invoice.invoice_date.strftime("%Y-%m"),
            created_by=invoice.created_by,
        )
        self.db.add(jv)
        await self.db.flush()

        line_no = 1
        self.db.add(
            JVLine(
                jv_id=jv.id,
                line_number=line_no,
                gl_account_id=cos_acct,
                debit_amount=invoice.subtotal,
                credit_amount=0.0,
                description=f"Cost of Sales - {invoice.invoice_number}",
                event_id=invoice.event_id,
            )
        )
        if invoice.tax_amount > 0 and vat_acct:
            line_no += 1
            self.db.add(
                JVLine(
                    jv_id=jv.id,
                    line_number=line_no,
                    gl_account_id=vat_acct,
                    debit_amount=invoice.tax_amount,
                    credit_amount=0.0,
                    description=f"VAT Input - {invoice.invoice_number}",
                    event_id=invoice.event_id,
                )
            )
        line_no += 1
        self.db.add(
            JVLine(
                jv_id=jv.id,
                line_number=line_no,
                gl_account_id=ap_acct,
                debit_amount=0.0,
                credit_amount=invoice.total_amount,
                description=f"AP - {invoice.invoice_number}",
                event_id=invoice.event_id,
            )
        )

        invoice.gl_posted = True
        invoice.gl_posted_at = datetime.utcnow()
        invoice.gl_posted_by = invoice.created_by
        return jv

    async def post_receipt(self, receipt: RCTHeader) -> JVHeader | None:
        if receipt.gl_posted:
            return None
        cash_acct = await self._resolve_account("cash")
        ar_acct = await self._resolve_account("accounts_receivable")
        if not all([cash_acct, ar_acct]):
            return None

        sn = SerialNumberService(self.db)
        jv_number = await sn.generate("JV", JVHeader)

        jv = JVHeader(
            jv_number=jv_number,
            jv_date=receipt.receipt_date,
            reference=f"Receipt {receipt.receipt_number}",
            description=f"Auto-posting for receipt {receipt.receipt_number}",
            total_debit=receipt.amount,
            total_credit=receipt.amount,
            status="Posted",
            gl_posted=True,
            gl_posted_at=datetime.utcnow(),
            gl_period=receipt.receipt_date.strftime("%Y-%m"),
            created_by=receipt.created_by,
        )
        self.db.add(jv)
        await self.db.flush()

        self.db.add(
            JVLine(
                jv_id=jv.id,
                line_number=1,
                gl_account_id=cash_acct,
                debit_amount=receipt.amount,
                credit_amount=0.0,
                description=f"Receipt - {receipt.receipt_number}",
            )
        )
        self.db.add(
            JVLine(
                jv_id=jv.id,
                line_number=2,
                gl_account_id=ar_acct,
                debit_amount=0.0,
                credit_amount=receipt.amount,
                description=f"AR Settlement - {receipt.receipt_number}",
            )
        )

        receipt.gl_posted = True
        receipt.gl_posted_at = datetime.utcnow()
        return jv

    async def post_payment(self, payment: PMTHeader) -> JVHeader | None:
        if payment.gl_posted:
            return None
        ap_acct = await self._resolve_account("accounts_payable")
        cash_acct = await self._resolve_account("cash")
        if not all([ap_acct, cash_acct]):
            return None

        sn = SerialNumberService(self.db)
        jv_number = await sn.generate("JV", JVHeader)

        jv = JVHeader(
            jv_number=jv_number,
            jv_date=payment.payment_date,
            reference=f"Payment {payment.payment_number}",
            description=f"Auto-posting for payment {payment.payment_number}",
            total_debit=payment.amount,
            total_credit=payment.amount,
            status="Posted",
            gl_posted=True,
            gl_posted_at=datetime.utcnow(),
            gl_period=payment.payment_date.strftime("%Y-%m"),
            created_by=payment.created_by,
        )
        self.db.add(jv)
        await self.db.flush()

        self.db.add(
            JVLine(
                jv_id=jv.id,
                line_number=1,
                gl_account_id=ap_acct,
                debit_amount=payment.amount,
                credit_amount=0.0,
                description=f"AP Settlement - {payment.payment_number}",
            )
        )
        self.db.add(
            JVLine(
                jv_id=jv.id,
                line_number=2,
                gl_account_id=cash_acct,
                debit_amount=0.0,
                credit_amount=payment.amount,
                description=f"Payment - {payment.payment_number}",
            )
        )

        payment.gl_posted = True
        payment.gl_posted_at = datetime.utcnow()
        return jv
