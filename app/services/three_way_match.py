from datetime import datetime
from datetime import timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.supplier import PurchaseOrder
from app.models.procurement import GRNHeader, GRNDetail
from app.models.finance import VendorInvoice
from app.models.three_way_match import ThreeWayMatch


class ThreeWayMatchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def perform_match(
        self,
        po_id: int,
        grn_id: int,
        invoice_id: int | None = None,
        auto_resolve: bool = True,
    ) -> ThreeWayMatch:
        po_result = await self.db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == po_id)
        )
        po = po_result.scalar_one_or_none()

        grn_result = await self.db.execute(
            select(GRNHeader).where(GRNHeader.id == grn_id)
        )
        grn = grn_result.scalar_one_or_none()

        if not po or not grn:
            raise ValueError("PO or GRN not found")

        po_qty = po.total_amount / (po.amount if po.amount > 0 else 1)
        grn_lines_result = await self.db.execute(
            select(GRNDetail).where(GRNDetail.grn_id == grn_id)
        )
        grn_lines = grn_lines_result.scalars().all()
        grn_qty = sum(line.accepted_qty for line in grn_lines)
        grn_price = sum(
            line.accepted_qty * (po.amount / max(po_qty, 1)) for line in grn_lines
        )

        qty_variance = grn_qty - po_qty
        qty_variance_pct = (qty_variance / po_qty * 100) if po_qty > 0 else 0
        qty_match = abs(qty_variance_pct) <= 5.0

        price_variance = grn_price - po.amount
        price_variance_pct = (price_variance / po.amount * 100) if po.amount > 0 else 0
        price_match = abs(price_variance_pct) <= 2.0

        invoice_price = 0.0
        if invoice_id:
            inv_result = await self.db.execute(
                select(VendorInvoice).where(VendorInvoice.id == invoice_id)
            )
            inv = inv_result.scalar_one_or_none()
            if inv:
                invoice_price = inv.total_amount
                inv_price_var = invoice_price - po.amount
                inv_price_pct = (
                    (inv_price_var / po.amount * 100) if po.amount > 0 else 0
                )
                price_match = abs(inv_price_pct) <= 2.0
                price_variance = inv_price_var

        if qty_match and price_match:
            overall_status = "matched"
        elif auto_resolve and (
            abs(qty_variance_pct) <= 10 or abs(price_variance_pct) <= 5
        ):
            overall_status = "tolerance"
        else:
            overall_status = "discrepancy"

        result = await self.db.execute(
            select(ThreeWayMatch).where(
                ThreeWayMatch.po_id == po_id,
                ThreeWayMatch.grn_id == grn_id,
            )
        )
        match = result.scalar_one_or_none()
        if not match:
            match = ThreeWayMatch(po_id=po_id, grn_id=grn_id, invoice_id=invoice_id)
            self.db.add(match)

        match.po_qty = po_qty
        match.grn_qty = grn_qty
        match.qty_variance = qty_variance
        match.qty_match = qty_match
        match.po_price = po.amount
        match.invoice_price = invoice_price if invoice_id else grn_price
        match.price_variance = price_variance
        match.price_match = price_match
        match.overall_status = overall_status
        match.match_date = datetime.utcnow()
        match.qty_tolerance_pct = 5.0
        match.price_tolerance_pct = 2.0

        if overall_status == "matched" or overall_status == "tolerance":
            grn.status = "Matched"
        else:
            grn.status = "Discrepancy"

        await self.db.commit()
        return match
