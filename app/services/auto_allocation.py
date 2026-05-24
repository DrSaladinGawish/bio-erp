from sqlalchemy import select, and_, asc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.finance import (
    CustomerInvoice,
    VendorInvoice,
    RCTAllocation,
    PMTAllocation,
)


class AutoAllocationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def auto_allocate_receipt(
        self,
        receipt_id: int,
        customer_id: int,
        amount: float,
        allocated_by: int,
    ) -> list[dict]:
        result = await self.db.execute(
            select(CustomerInvoice)
            .where(
                and_(
                    CustomerInvoice.customer_id == customer_id,
                    CustomerInvoice.status.in_(["Sent", "Partial"]),
                    CustomerInvoice.amount_due > 0,
                )
            )
            .order_by(asc(CustomerInvoice.invoice_date))
        )
        invoices = result.scalars().all()
        if not invoices:
            return []

        remaining = amount
        allocations = []
        for inv in invoices:
            if remaining <= 0:
                break
            due = inv.amount_due
            alloc_amount = min(remaining, due)
            bal_before = due
            bal_after = due - alloc_amount

            allocation = RCTAllocation(
                receipt_id=receipt_id,
                invoice_id=inv.id,
                amount_allocated=alloc_amount,
                discount_taken=0.0,
                invoice_balance_before=bal_before,
                invoice_balance_after=bal_after,
                allocated_by=allocated_by,
            )
            self.db.add(allocation)

            inv.amount_paid = (inv.amount_paid or 0) + alloc_amount
            inv.amount_due = bal_after
            inv.status = "Paid" if bal_after <= 0 else "Partial"

            allocations.append(
                {
                    "invoice_id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "amount_allocated": alloc_amount,
                    "balance_after": bal_after,
                }
            )
            remaining -= alloc_amount

        await self.db.commit()
        return allocations

    async def auto_allocate_payment(
        self,
        payment_id: int,
        vendor_id: int,
        amount: float,
        allocated_by: int,
    ) -> list[dict]:
        result = await self.db.execute(
            select(VendorInvoice)
            .where(
                and_(
                    VendorInvoice.vendor_id == vendor_id,
                    VendorInvoice.status.in_(["Unpaid", "Partial"]),
                    VendorInvoice.amount_due > 0,
                )
            )
            .order_by(asc(VendorInvoice.invoice_date))
        )
        invoices = result.scalars().all()
        if not invoices:
            return []

        remaining = amount
        allocations = []
        for inv in invoices:
            if remaining <= 0:
                break
            due = inv.amount_due
            alloc_amount = min(remaining, due)
            bal_before = due
            bal_after = due - alloc_amount

            allocation = PMTAllocation(
                payment_id=payment_id,
                invoice_id=inv.id,
                amount_allocated=alloc_amount,
                discount_taken=0.0,
                invoice_balance_before=bal_before,
                invoice_balance_after=bal_after,
                allocated_by=allocated_by,
            )
            self.db.add(allocation)

            inv.amount_paid = (inv.amount_paid or 0) + alloc_amount
            inv.amount_due = bal_after
            inv.status = "Paid" if bal_after <= 0 else "Partial"

            allocations.append(
                {
                    "invoice_id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "amount_allocated": alloc_amount,
                    "balance_after": bal_after,
                }
            )
            remaining -= alloc_amount

        await self.db.commit()
        return allocations
