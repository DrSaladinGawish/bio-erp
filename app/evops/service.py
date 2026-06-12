"""service.py — Business logic for Event Operations"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.evops.models import (
    EvOps_Event, EvOps_Task, EvOps_Milestone,
    EvOps_Resource, EvOps_Note,
    EventStatus, TaskStatus
)
from app.evops.schemas import (
    EventCreate, EventUpdate,
    TaskCreate, TaskUpdate,
    MilestoneCreate, ResourceCreate, NoteCreate
)


class EventOpsService:

    @staticmethod
    def list_events(
        db: Session,
        status: Optional[EventStatus] = None,
        event_type: Optional[str] = None,
        client_id: Optional[int] = None,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ):
        q = db.query(EvOps_Event)
        if status:      q = q.filter(EvOps_Event.status == status)
        if event_type:  q = q.filter(EvOps_Event.event_type == event_type)
        if client_id:   q = q.filter(EvOps_Event.client_id == client_id)
        if active_only: q = q.filter(EvOps_Event.is_active == True)
        total  = q.count()
        active = db.query(EvOps_Event).filter(
            EvOps_Event.status.in_([
                EventStatus.CONFIRMED, EventStatus.IN_PROGRESS
            ])
        ).count()
        items = q.order_by(EvOps_Event.created_at.desc()).offset(skip).limit(limit).all()
        for ev in items:
            ev.task_count = len(ev.tasks)
            ev.tasks_done = sum(1 for t in ev.tasks if t.status == TaskStatus.DONE)
        return total, active, items

    @staticmethod
    def get_event(db: Session, event_id: int) -> EvOps_Event | None:
        return db.query(EvOps_Event).filter(EvOps_Event.id == event_id).first()

    @staticmethod
    def get_event_by_pnr(db: Session, pnr_ref: str) -> EvOps_Event | None:
        return db.query(EvOps_Event).filter(EvOps_Event.pnr_ref == pnr_ref).first()

    @staticmethod
    def create_event(db: Session, data: EventCreate) -> EvOps_Event:
        ev = EvOps_Event(**data.model_dump())
        db.add(ev)
        db.commit()
        db.refresh(ev)
        return ev

    @staticmethod
    def update_event(db: Session, event_id: int, data: EventUpdate) -> EvOps_Event | None:
        ev = EventOpsService.get_event(db, event_id)
        if not ev:
            return None
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(ev, field, val)
        ev.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ev)
        return ev

    @staticmethod
    def transition_status(db: Session, event_id: int, new_status: EventStatus) -> EvOps_Event | None:
        ALLOWED = {
            EventStatus.DRAFT:       [EventStatus.PLANNED, EventStatus.CANCELLED],
            EventStatus.PLANNED:     [EventStatus.CONFIRMED, EventStatus.CANCELLED, EventStatus.ON_HOLD],
            EventStatus.CONFIRMED:   [EventStatus.IN_PROGRESS, EventStatus.CANCELLED, EventStatus.ON_HOLD],
            EventStatus.IN_PROGRESS: [EventStatus.COMPLETED, EventStatus.CANCELLED, EventStatus.ON_HOLD],
            EventStatus.ON_HOLD:     [EventStatus.PLANNED, EventStatus.CANCELLED],
            EventStatus.COMPLETED:   [],
            EventStatus.CANCELLED:   [],
        }
        ev = EventOpsService.get_event(db, event_id)
        if not ev:
            return None
        if new_status not in ALLOWED.get(ev.status, []):
            raise ValueError(
                f"Cannot transition from {ev.status} -> {new_status}. "
                f"Allowed: {ALLOWED.get(ev.status, [])}"
            )
        ev.status = new_status
        ev.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(ev)
        return ev

    @staticmethod
    def delete_event(db: Session, event_id: int) -> bool:
        ev = EventOpsService.get_event(db, event_id)
        if not ev:
            return False
        ev.is_active = False
        ev.updated_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def add_task(db: Session, event_id: int, data: TaskCreate) -> EvOps_Task:
        task = EvOps_Task(event_id=event_id, **data.model_dump())
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update_task(db: Session, task_id: int, data: TaskUpdate) -> EvOps_Task | None:
        task = db.query(EvOps_Task).filter(EvOps_Task.id == task_id).first()
        if not task:
            return None
        for field, val in data.model_dump(exclude_unset=True).items():
            setattr(task, field, val)
        if data.status == TaskStatus.DONE and not task.completed_at:
            task.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete_task(db: Session, task_id: int) -> bool:
        task = db.query(EvOps_Task).filter(EvOps_Task.id == task_id).first()
        if not task:
            return False
        db.delete(task)
        db.commit()
        return True

    @staticmethod
    def add_milestone(db: Session, event_id: int, data: MilestoneCreate) -> EvOps_Milestone:
        ms = EvOps_Milestone(event_id=event_id, **data.model_dump())
        db.add(ms)
        db.commit()
        db.refresh(ms)
        return ms

    @staticmethod
    def achieve_milestone(db: Session, milestone_id: int) -> EvOps_Milestone | None:
        ms = db.query(EvOps_Milestone).filter(EvOps_Milestone.id == milestone_id).first()
        if not ms:
            return None
        ms.is_achieved = True
        ms.achieved_at = datetime.utcnow()
        db.commit()
        db.refresh(ms)
        return ms

    @staticmethod
    def add_resource(db: Session, event_id: int, data: ResourceCreate) -> EvOps_Resource:
        res = EvOps_Resource(event_id=event_id, **data.model_dump())
        db.add(res)
        ev = EventOpsService.get_event(db, event_id)
        if ev:
            ev.actual_cost_egp = sum(
                r.total_cost_egp for r in ev.resources
            ) + res.total_cost_egp
        db.commit()
        db.refresh(res)
        return res

    @staticmethod
    def add_note(db: Session, event_id: int, data: NoteCreate) -> EvOps_Note:
        note = EvOps_Note(event_id=event_id, **data.model_dump())
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    @staticmethod
    def get_stats(db: Session) -> dict:
        events = db.query(EvOps_Event).filter(EvOps_Event.is_active == True).all()
        now = datetime.utcnow()
        next30 = now + timedelta(days=30)

        by_status   = {}
        by_priority = {}
        total_budget = 0.0
        total_cost   = 0.0
        task_total   = 0
        task_done    = 0

        for ev in events:
            by_status[ev.status.value]   = by_status.get(ev.status.value, 0) + 1
            by_priority[ev.priority.value] = by_priority.get(ev.priority.value, 0) + 1
            total_budget += ev.budget_egp or 0
            total_cost   += ev.actual_cost_egp or 0
            for t in ev.tasks:
                task_total += 1
                if t.status == TaskStatus.DONE:
                    task_done += 1

        upcoming = sum(
            1 for ev in events
            if ev.start_date and now <= ev.start_date <= next30
        )

        return {
            "total_events":       len(events),
            "by_status":          by_status,
            "by_priority":        by_priority,
            "total_budget_egp":   total_budget,
            "total_cost_egp":     total_cost,
            "budget_utilization": round(total_cost / total_budget * 100, 1)
                                  if total_budget else 0,
            "avg_task_completion": round(task_done / task_total * 100, 1)
                                   if task_total else 0,
            "upcoming_events":    upcoming,
        }
