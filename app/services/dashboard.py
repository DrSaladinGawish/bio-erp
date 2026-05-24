from datetime import date
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.event import Event
from app.models.finance import CustomerInvoice, VendorInvoice, RCTHeader, PMTHeader
from app.models.client import Client
from app.models.supplier import Supplier


class DashboardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_panel_1_revenue_kpi(self):
        """Total revenue, invoiced, collected, outstanding AR"""
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(CustomerInvoice.total_amount), 0).label(
                    "total_invoiced"
                ),
                func.coalesce(func.sum(CustomerInvoice.amount_paid), 0).label(
                    "total_collected"
                ),
                func.coalesce(func.sum(CustomerInvoice.amount_due), 0).label(
                    "total_outstanding"
                ),
            ).where(CustomerInvoice.is_active)
        )
        row = result.one()
        return {
            "total_invoiced": float(row.total_invoiced),
            "total_collected": float(row.total_collected),
            "total_outstanding": float(row.total_outstanding),
            "collection_rate": round(
                float(row.total_collected) / float(row.total_invoiced) * 100, 1
            )
            if float(row.total_invoiced) > 0
            else 0,
        }

    async def get_panel_2_expense_kpi(self):
        """Total expenses, paid, outstanding AP"""
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(VendorInvoice.total_amount), 0).label(
                    "total_billed"
                ),
                func.coalesce(func.sum(VendorInvoice.amount_paid), 0).label(
                    "total_paid"
                ),
                func.coalesce(func.sum(VendorInvoice.amount_due), 0).label(
                    "total_unpaid"
                ),
            ).where(VendorInvoice.is_active)
        )
        row = result.one()
        return {
            "total_billed": float(row.total_billed),
            "total_paid": float(row.total_paid),
            "total_unpaid": float(row.total_unpaid),
            "payment_rate": round(
                float(row.total_paid) / float(row.total_billed) * 100, 1
            )
            if float(row.total_billed) > 0
            else 0,
        }

    async def get_panel_3_event_pipeline(self):
        """Event counts by status"""
        result = await self.db.execute(
            select(Event.status, func.count(Event.id).label("count"))
            .where(Event.is_active)
            .group_by(Event.status)
        )
        rows = result.all()
        total = sum(r.count for r in rows)
        return {
            "total_events": total,
            "by_status": {r.status: r.count for r in rows},
        }

    async def get_panel_4_budget_health(self):
        """Budget vs actual across all events"""
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(Event.total_budget), 0).label("total_budget"),
                func.coalesce(func.sum(Event.total_cost), 0).label("total_cost"),
                func.coalesce(func.sum(Event.total_revenue), 0).label("total_revenue"),
                func.coalesce(func.sum(Event.gross_profit), 0).label("total_profit"),
            ).where(Event.is_active)
        )
        row = result.one()
        return {
            "total_budget": float(row.total_budget),
            "total_cost": float(row.total_cost),
            "total_revenue": float(row.total_revenue),
            "total_profit": float(row.total_profit),
            "profit_margin": round(
                float(row.total_profit) / float(row.total_revenue) * 100, 1
            )
            if float(row.total_revenue) > 0
            else 0,
            "budget_utilization": round(
                float(row.total_cost) / float(row.total_budget) * 100, 1
            )
            if float(row.total_budget) > 0
            else 0,
        }

    async def get_panel_5_recent_transactions(self, limit: int = 10):
        """Most recent financial activity"""
        receipts = await self.db.execute(
            select(RCTHeader).order_by(RCTHeader.created_at.desc()).limit(limit)
        )
        payments = await self.db.execute(
            select(PMTHeader).order_by(PMTHeader.created_at.desc()).limit(limit)
        )
        ar = await self.db.execute(
            select(CustomerInvoice)
            .order_by(CustomerInvoice.created_at.desc())
            .limit(limit)
        )
        ap = await self.db.execute(
            select(VendorInvoice).order_by(VendorInvoice.created_at.desc()).limit(limit)
        )
        return {
            "recent_receipts": [
                {
                    "id": r.id,
                    "number": r.receipt_number,
                    "amount": r.amount,
                    "date": r.receipt_date,
                    "status": r.status,
                }
                for r in receipts.scalars().all()
            ],
            "recent_payments": [
                {
                    "id": p.id,
                    "number": p.payment_number,
                    "amount": p.amount,
                    "date": p.payment_date,
                    "status": p.status,
                }
                for p in payments.scalars().all()
            ],
            "recent_ar": [
                {
                    "id": i.id,
                    "number": i.invoice_number,
                    "amount": i.total_amount,
                    "date": i.invoice_date,
                    "status": i.status,
                }
                for i in ar.scalars().all()
            ],
            "recent_ap": [
                {
                    "id": i.id,
                    "number": i.invoice_number,
                    "amount": i.total_amount,
                    "date": i.invoice_date,
                    "status": i.status,
                }
                for i in ap.scalars().all()
            ],
        }

    async def get_panel_6_ar_aging_summary(self):
        """AR aging buckets"""
        today = date.today()
        result = await self.db.execute(
            select(CustomerInvoice).where(
                CustomerInvoice.is_active,
                CustomerInvoice.status.in_(["Sent", "Partial"]),
            )
        )
        invoices = result.scalars().all()
        buckets = {"0-30": 0.0, "31-60": 0.0, "61-90": 0.0, "90+": 0.0}
        for inv in invoices:
            if inv.due_date:
                days = (today - inv.due_date).days
                if days <= 30:
                    buckets["0-30"] += inv.amount_due
                elif days <= 60:
                    buckets["31-60"] += inv.amount_due
                elif days <= 90:
                    buckets["61-90"] += inv.amount_due
                else:
                    buckets["90+"] += inv.amount_due
        return {"buckets": buckets, "total_outstanding": sum(buckets.values())}

    async def get_panel_7_upcoming_events(self, limit: int = 5):
        """Upcoming events by start date"""
        result = await self.db.execute(
            select(Event)
            .where(
                Event.is_active,
                Event.status.in_(["BUDGETED", "APPROVED", "IN_PROGRESS"]),
            )
            .order_by(Event.start_date.asc())
            .limit(limit)
        )
        events = result.scalars().all()
        return [
            {
                "id": e.id,
                "event_code": e.event_code,
                "name_en": e.name_en,
                "start_date": e.start_date,
                "status": e.status,
                "total_budget": e.total_budget,
            }
            for e in events
        ]

    async def get_panel_8_customer_supplier_counts(self):
        """Client and supplier summary"""
        clients_count = await self.db.execute(
            select(func.count(Client.id)).where(Client.is_active)
        )
        suppliers_count = await self.db.execute(
            select(func.count(Supplier.id)).where(Supplier.is_active)
        )
        return {
            "active_clients": clients_count.scalar(),
            "active_suppliers": suppliers_count.scalar(),
        }

    async def get_full_dashboard(self):
        """All 8 panels in one call"""
        return {
            "revenue_kpi": await self.get_panel_1_revenue_kpi(),
            "expense_kpi": await self.get_panel_2_expense_kpi(),
            "event_pipeline": await self.get_panel_3_event_pipeline(),
            "budget_health": await self.get_panel_4_budget_health(),
            "recent_transactions": await self.get_panel_5_recent_transactions(),
            "ar_aging": await self.get_panel_6_ar_aging_summary(),
            "upcoming_events": await self.get_panel_7_upcoming_events(),
            "counts": await self.get_panel_8_customer_supplier_counts(),
        }
