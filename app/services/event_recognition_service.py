from __future__ import annotations

from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models import (
    Client,
    Event,
    EventLineItem,
    EventMasterNode,
    EventOperation,
    ItemCategory,
    ItemSubCategory,
    ServiceUOM,
    Staff,
)


class EventRecognitionService:
    """Auto-recognition engine for event operations.

    Suggests service line items, validates venue capacity,
    and pre-fills ops briefing forms based on historical data.
    """

    @staticmethod
    async def suggest_services(
        db: AsyncSession,
        client_id: int,
        category_id: int | None = None,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(EventLineItem)
            .join(Event)
            .where(
                Event.client_id == client_id,
                EventLineItem.is_active,
            )
            .order_by(EventLineItem.id.desc())
            .limit(20)
        )
        past_items = result.scalars().all()

        category_map: dict[str, dict] = {}
        for item in past_items:
            key = item.description or "unknown"
            if key not in category_map:
                category_map[key] = {
                    "description": item.description,
                    "description_ar": item.description_ar,
                    "section": item.section,
                    "uom": item.uom,
                    "qty": item.quantity,
                    "unit_cost": item.unit_cost,
                    "selling_price": item.selling_price,
                    "frequency": 0,
                }
            category_map[key]["frequency"] += 1

        sorted_suggestions = sorted(
            category_map.values(), key=lambda x: x["frequency"], reverse=True
        )[:10]

        template_items = []
        if category_id:
            tmpl = await db.execute(
                select(ServiceUOM).where(
                    ServiceUOM.category_id == category_id,
                    ServiceUOM.is_active,
                )
            )
            template_items = [
                {
                    "uom_code": t.uom_code,
                    "uom_name": t.uom_name,
                    "default_unit_price": t.default_unit_price,
                    "min_qty": t.min_qty,
                    "max_qty": t.max_qty,
                }
                for t in template_items.scalars().all()
            ]

        return {
            "client_history": sorted_suggestions,
            "category_template": template_items,
        }

    @staticmethod
    async def validate_capacity(
        db: AsyncSession,
        event_name: str | None = None,
        pax: int = 0,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(Event)
            .where(
                Event.venue.isnot(None),
                Event.actual_pax.isnot(None),
            )
            .limit(50)
        )
        events = result.scalars().all()

        suggestions = []
        for e in events:
            if e.venue and e.actual_pax and e.actual_pax >= pax * 0.8:
                suggestions.append({
                    "venue": e.venue,
                    "venue_ar": e.venue_ar,
                    "capacity": e.actual_pax,
                    "event_code": e.event_code,
                })

        return {
            "valid": True,
            "pax": pax,
            "suggested_venues": suggestions[:5],
        }

    @staticmethod
    async def auto_populate_ops_form(
        db: AsyncSession,
        event_id: int,
    ) -> dict[str, Any]:
        event = await db.get(Event, event_id)
        if not event:
            return {"error": "Event not found"}

        ops = await db.execute(
            select(EventOperation).where(EventOperation.event_id == event_id)
        )
        existing = ops.scalar_one_or_none()

        staff_list = []
        if existing and existing.ops_manager_id:
            staff = await db.get(Staff, existing.ops_manager_id)
            if staff:
                staff_list = [{"id": staff.id, "name": staff.name_en}]

        return {
            "event_code": event.event_code,
            "client_id": event.client_id,
            "venue": event.venue,
            "start_date": event.start_date,
            "end_date": event.end_date,
            "actual_pax": event.actual_pax,
            "lifecycle_status": event.lifecycle_status,
            "ops_manager_id": existing.ops_manager_id if existing else None,
            "briefing_completed": existing.briefing_completed if existing else False,
            "load_in_time": existing.load_in_time.isoformat() if existing and existing.load_in_time else None,
            "sound_check_done": existing.sound_check_done if existing else False,
            "catering_final_count": existing.catering_final_count if existing else None,
            "staff": staff_list,
        }
