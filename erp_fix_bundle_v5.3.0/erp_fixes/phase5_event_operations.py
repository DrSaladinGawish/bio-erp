"""
phase5_event_operations/
========================
Full Event Operations module (Phase 5).

Structure delivered here:
  models/event_ops.py        — SQLAlchemy ORM models
  schemas/event_ops.py       — Pydantic v2 request/response schemas
  services/event_ops.py      — Business logic / service layer
  routers/event_ops_router.py — FastAPI router (mount in main.py)
  migrations/add_event_ops.py — Alembic-compatible migration helper

This file is a MONOLITH for delivery; split into the paths shown above
before integrating into your project.

Mount in main.py:
    from routers.event_ops_router import router as event_ops_router
    app.include_router(event_ops_router, prefix="/api/v1/evops", tags=["Event Operations"])
"""

# =============================================================================
# ── SECTION 1: models/event_ops.py ───────────────────────────────────────────
# =============================================================================
EVENT_OPS_MODELS = '''
"""models/event_ops.py — Event Operations ORM models"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean,
    Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

# Import your project's Base — adjust path as needed
try:
    from app.database import Base
except ImportError:
    from database import Base


class EventStatus(str, enum.Enum):
    DRAFT       = "draft"
    PLANNED     = "planned"
    CONFIRMED   = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    CANCELLED   = "cancelled"
    ON_HOLD     = "on_hold"


class EventPriority(str, enum.Enum):
    LOW      = "low"
    NORMAL   = "normal"
    HIGH     = "high"
    CRITICAL = "critical"


class TaskStatus(str, enum.Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    DONE        = "done"
    BLOCKED     = "blocked"
    CANCELLED   = "cancelled"


class EvOps_Event(Base):
    """Core event / PNR record."""
    __tablename__ = "evops_events"

    id              = Column(Integer, primary_key=True, index=True)
    pnr_ref         = Column(String(50), unique=True, index=True, nullable=False)
    title           = Column(String(200), nullable=False)
    description     = Column(Text, nullable=True)
    client_id       = Column(Integer, ForeignKey("Clnt_Mtbl.id"), nullable=True)
    event_type      = Column(String(80), nullable=False, default="general")
    status          = Column(SAEnum(EventStatus), default=EventStatus.DRAFT, index=True)
    priority        = Column(SAEnum(EventPriority), default=EventPriority.NORMAL)
    start_date      = Column(DateTime, nullable=True)
    end_date        = Column(DateTime, nullable=True)
    venue           = Column(String(200), nullable=True)
    location        = Column(String(200), nullable=True)
    budget_egp      = Column(Float, default=0.0)
    actual_cost_egp = Column(Float, default=0.0)
    attendees_est   = Column(Integer, default=0)
    attendees_actual= Column(Integer, default=0)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by      = Column(String(80), nullable=True)

    # Relationships
    tasks           = relationship("EvOps_Task",    back_populates="event", cascade="all, delete-orphan")
    milestones      = relationship("EvOps_Milestone", back_populates="event", cascade="all, delete-orphan")
    resources       = relationship("EvOps_Resource", back_populates="event", cascade="all, delete-orphan")
    notes           = relationship("EvOps_Note",    back_populates="event", cascade="all, delete-orphan")


class EvOps_Task(Base):
    """Task checklist item within an event."""
    __tablename__ = "evops_tasks"

    id          = Column(Integer, primary_key=True, index=True)
    event_id    = Column(Integer, ForeignKey("evops_events.id"), nullable=False, index=True)
    title       = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    assignee    = Column(String(100), nullable=True)
    status      = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    due_date    = Column(DateTime, nullable=True)
    completed_at= Column(DateTime, nullable=True)
    sort_order  = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)

    event       = relationship("EvOps_Event", back_populates="tasks")


class EvOps_Milestone(Base):
    """Key milestone / gate within an event."""
    __tablename__ = "evops_milestones"

    id          = Column(Integer, primary_key=True, index=True)
    event_id    = Column(Integer, ForeignKey("evops_events.id"), nullable=False, index=True)
    name        = Column(String(200), nullable=False)
    target_date = Column(DateTime, nullable=False)
    achieved_at = Column(DateTime, nullable=True)
    is_achieved = Column(Boolean, default=False)
    notes       = Column(Text, nullable=True)

    event       = relationship("EvOps_Event", back_populates="milestones")


class EvOps_Resource(Base):
    """Resource allocation to an event (staff, equipment, venue)."""
    __tablename__ = "evops_resources"

    id              = Column(Integer, primary_key=True, index=True)
    event_id        = Column(Integer, ForeignKey("evops_events.id"), nullable=False, index=True)
    resource_type   = Column(String(50), nullable=False)  # staff | equipment | venue | vendor
    name            = Column(String(200), nullable=False)
    quantity        = Column(Float, default=1.0)
    unit_cost_egp   = Column(Float, default=0.0)
    total_cost_egp  = Column(Float, default=0.0)
    supplier_id     = Column(Integer, nullable=True)
    confirmed       = Column(Boolean, default=False)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    event           = relationship("EvOps_Event", back_populates="resources")


class EvOps_Note(Base):
    """Free-text note / log entry for an event."""
    __tablename__ = "evops_notes"

    id          = Column(Integer, primary_key=True, index=True)
    event_id    = Column(Integer, ForeignKey("evops_events.id"), nullable=False, index=True)
    body        = Column(Text, nullable=False)
    author      = Column(String(100), nullable=True)
    is_internal = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    event       = relationship("EvOps_Event", back_populates="notes")
'''

# =============================================================================
# ── SECTION 2: schemas/event_ops.py ──────────────────────────────────────────
# =============================================================================
EVENT_OPS_SCHEMAS = '''
"""schemas/event_ops.py — Pydantic v2 schemas for Event Operations"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

from models.event_ops import EventStatus, EventPriority, TaskStatus


# ── Task ──────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title:       str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assignee:    Optional[str] = None
    status:      TaskStatus = TaskStatus.PENDING
    due_date:    Optional[datetime] = None
    sort_order:  int = 0

class TaskUpdate(BaseModel):
    title:       Optional[str] = None
    description: Optional[str] = None
    assignee:    Optional[str] = None
    status:      Optional[TaskStatus] = None
    due_date:    Optional[datetime] = None
    completed_at:Optional[datetime] = None

class TaskOut(BaseModel):
    id:          int
    event_id:    int
    title:       str
    assignee:    Optional[str]
    status:      TaskStatus
    due_date:    Optional[datetime]
    completed_at:Optional[datetime]
    sort_order:  int
    created_at:  datetime
    model_config = {"from_attributes": True}


# ── Milestone ─────────────────────────────────────────────────────────────────

class MilestoneCreate(BaseModel):
    name:        str = Field(..., min_length=1)
    target_date: datetime
    notes:       Optional[str] = None

class MilestoneUpdate(BaseModel):
    name:        Optional[str] = None
    target_date: Optional[datetime] = None
    achieved_at: Optional[datetime] = None
    is_achieved: Optional[bool] = None
    notes:       Optional[str] = None

class MilestoneOut(BaseModel):
    id:          int
    event_id:    int
    name:        str
    target_date: datetime
    achieved_at: Optional[datetime]
    is_achieved: bool
    notes:       Optional[str]
    model_config = {"from_attributes": True}


# ── Resource ──────────────────────────────────────────────────────────────────

class ResourceCreate(BaseModel):
    resource_type: str = Field(..., pattern=r"^(staff|equipment|venue|vendor)$")
    name:          str = Field(..., min_length=1)
    quantity:      float = 1.0
    unit_cost_egp: float = 0.0
    supplier_id:   Optional[int] = None
    confirmed:     bool = False
    notes:         Optional[str] = None

    @model_validator(mode="after")
    def compute_total(self):
        self.total_cost_egp = self.quantity * self.unit_cost_egp
        return self

    total_cost_egp: float = 0.0

class ResourceOut(BaseModel):
    id:            int
    event_id:      int
    resource_type: str
    name:          str
    quantity:      float
    unit_cost_egp: float
    total_cost_egp:float
    confirmed:     bool
    notes:         Optional[str]
    model_config = {"from_attributes": True}


# ── Note ──────────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    body:       str = Field(..., min_length=1)
    author:     Optional[str] = None
    is_internal:bool = True

class NoteOut(BaseModel):
    id:         int
    event_id:   int
    body:       str
    author:     Optional[str]
    is_internal:bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Event ─────────────────────────────────────────────────────────────────────

class EventCreate(BaseModel):
    pnr_ref:      str = Field(..., min_length=1, max_length=50)
    title:        str = Field(..., min_length=1, max_length=200)
    description:  Optional[str] = None
    client_id:    Optional[int] = None
    event_type:   str = "general"
    status:       EventStatus = EventStatus.DRAFT
    priority:     EventPriority = EventPriority.NORMAL
    start_date:   Optional[datetime] = None
    end_date:     Optional[datetime] = None
    venue:        Optional[str] = None
    location:     Optional[str] = None
    budget_egp:   float = 0.0
    attendees_est:int = 0
    created_by:   Optional[str] = None

class EventUpdate(BaseModel):
    title:           Optional[str] = None
    description:     Optional[str] = None
    client_id:       Optional[int] = None
    event_type:      Optional[str] = None
    status:          Optional[EventStatus] = None
    priority:        Optional[EventPriority] = None
    start_date:      Optional[datetime] = None
    end_date:        Optional[datetime] = None
    venue:           Optional[str] = None
    location:        Optional[str] = None
    budget_egp:      Optional[float] = None
    actual_cost_egp: Optional[float] = None
    attendees_est:   Optional[int] = None
    attendees_actual:Optional[int] = None

class EventSummary(BaseModel):
    id:              int
    pnr_ref:         str
    title:           str
    event_type:      str
    status:          EventStatus
    priority:        EventPriority
    start_date:      Optional[datetime]
    end_date:        Optional[datetime]
    budget_egp:      float
    actual_cost_egp: float
    task_count:      int = 0
    tasks_done:      int = 0
    is_active:       bool
    created_at:      datetime
    model_config = {"from_attributes": True}

class EventDetail(EventSummary):
    description:     Optional[str]
    client_id:       Optional[int]
    venue:           Optional[str]
    location:        Optional[str]
    attendees_est:   int
    attendees_actual:int
    tasks:           List[TaskOut] = []
    milestones:      List[MilestoneOut] = []
    resources:       List[ResourceOut] = []
    notes:           List[NoteOut] = []

class EventListResponse(BaseModel):
    total:  int
    active: int
    items:  List[EventSummary]

class EventStatsResponse(BaseModel):
    total_events:      int
    by_status:         dict
    by_priority:       dict
    total_budget_egp:  float
    total_cost_egp:    float
    budget_utilization:float    # cost/budget %
    avg_task_completion:float   # % tasks done
    upcoming_events:   int      # start_date in next 30 days
'''

# =============================================================================
# ── SECTION 3: services/event_ops.py ─────────────────────────────────────────
# =============================================================================
EVENT_OPS_SERVICE = '''
"""services/event_ops.py — Business logic for Event Operations"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from models.event_ops import (
    EvOps_Event, EvOps_Task, EvOps_Milestone,
    EvOps_Resource, EvOps_Note,
    EventStatus, TaskStatus
)
from schemas.event_ops import (
    EventCreate, EventUpdate,
    TaskCreate, TaskUpdate,
    MilestoneCreate, MilestoneUpdate,
    ResourceCreate, NoteCreate
)


class EventOpsService:

    # ── Events ────────────────────────────────────────────────────────────────

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
        # attach computed task counts
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
        """Status machine — enforces valid transitions."""
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
                f"Cannot transition from {ev.status} → {new_status}. "
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

    # ── Tasks ─────────────────────────────────────────────────────────────────

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

    # ── Milestones ────────────────────────────────────────────────────────────

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

    # ── Resources ─────────────────────────────────────────────────────────────

    @staticmethod
    def add_resource(db: Session, event_id: int, data: ResourceCreate) -> EvOps_Resource:
        res = EvOps_Resource(event_id=event_id, **data.model_dump())
        db.add(res)
        # update actual cost on parent event
        ev = EventOpsService.get_event(db, event_id)
        if ev:
            ev.actual_cost_egp = sum(
                r.total_cost_egp for r in ev.resources
            ) + res.total_cost_egp
        db.commit()
        db.refresh(res)
        return res

    # ── Notes ─────────────────────────────────────────────────────────────────

    @staticmethod
    def add_note(db: Session, event_id: int, data: NoteCreate) -> EvOps_Note:
        note = EvOps_Note(event_id=event_id, **data.model_dump())
        db.add(note)
        db.commit()
        db.refresh(note)
        return note

    # ── Analytics ─────────────────────────────────────────────────────────────

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
'''

# =============================================================================
# ── SECTION 4: routers/event_ops_router.py ───────────────────────────────────
# =============================================================================
EVENT_OPS_ROUTER = '''
"""routers/event_ops_router.py — FastAPI router for Event Operations (Phase 5)"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from models.event_ops import EventStatus, EventPriority
from schemas.event_ops import (
    EventCreate, EventUpdate, EventDetail, EventSummary,
    EventListResponse, EventStatsResponse,
    TaskCreate, TaskUpdate, TaskOut,
    MilestoneCreate, MilestoneUpdate, MilestoneOut,
    ResourceCreate, ResourceOut,
    NoteCreate, NoteOut,
)
from services.event_ops import EventOpsService

try:
    from app.database import get_db
except ImportError:
    from database import get_db

router = APIRouter()


# ── Summary / Stats ───────────────────────────────────────────────────────────

@router.get("/summary", response_model=EventListResponse, summary="List all events")
def list_events(
    status:     Optional[EventStatus]  = None,
    event_type: Optional[str]          = None,
    client_id:  Optional[int]          = None,
    active_only:bool                   = False,
    skip:       int                    = Query(0,   ge=0),
    limit:      int                    = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    total, active, items = EventOpsService.list_events(
        db, status, event_type, client_id, active_only, skip, limit
    )
    return {"total": total, "active": active, "items": items}


@router.get("/stats", response_model=EventStatsResponse, summary="Event KPI statistics")
def event_stats(db: Session = Depends(get_db)):
    return EventOpsService.get_stats(db)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/", response_model=EventDetail, status_code=status.HTTP_201_CREATED)
def create_event(data: EventCreate, db: Session = Depends(get_db)):
    if EventOpsService.get_event_by_pnr(db, data.pnr_ref):
        raise HTTPException(409, f"PNR '{data.pnr_ref}' already exists")
    return EventOpsService.create_event(db, data)


@router.get("/{event_id}", response_model=EventDetail)
def get_event(event_id: int, db: Session = Depends(get_db)):
    ev = EventOpsService.get_event(db, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    ev.task_count = len(ev.tasks)
    ev.tasks_done = sum(1 for t in ev.tasks if t.status.value == "done")
    return ev


@router.get("/pnr/{pnr_ref}", response_model=EventDetail, summary="Get event by PNR")
def get_event_by_pnr(pnr_ref: str, db: Session = Depends(get_db)):
    ev = EventOpsService.get_event_by_pnr(db, pnr_ref)
    if not ev:
        raise HTTPException(404, f"PNR '{pnr_ref}' not found")
    return ev


@router.patch("/{event_id}", response_model=EventDetail)
def update_event(event_id: int, data: EventUpdate, db: Session = Depends(get_db)):
    ev = EventOpsService.update_event(db, event_id, data)
    if not ev:
        raise HTTPException(404, "Event not found")
    return ev


@router.patch("/{event_id}/status", response_model=EventDetail, summary="Transition event status")
def transition_status(
    event_id:   int,
    new_status: EventStatus,
    db: Session = Depends(get_db),
):
    try:
        ev = EventOpsService.transition_status(db, event_id, new_status)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ev:
        raise HTTPException(404, "Event not found")
    return ev


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_event(event_id: int, db: Session = Depends(get_db)):
    if not EventOpsService.delete_event(db, event_id):
        raise HTTPException(404, "Event not found")


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.post("/{event_id}/tasks", response_model=TaskOut, status_code=201)
def add_task(event_id: int, data: TaskCreate, db: Session = Depends(get_db)):
    if not EventOpsService.get_event(db, event_id):
        raise HTTPException(404, "Event not found")
    return EventOpsService.add_task(db, event_id, data)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    task = EventOpsService.update_task(db, task_id, data)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    if not EventOpsService.delete_task(db, task_id):
        raise HTTPException(404, "Task not found")


# ── Milestones ────────────────────────────────────────────────────────────────

@router.post("/{event_id}/milestones", response_model=MilestoneOut, status_code=201)
def add_milestone(event_id: int, data: MilestoneCreate, db: Session = Depends(get_db)):
    if not EventOpsService.get_event(db, event_id):
        raise HTTPException(404, "Event not found")
    return EventOpsService.add_milestone(db, event_id, data)


@router.patch("/milestones/{milestone_id}/achieve", response_model=MilestoneOut)
def achieve_milestone(milestone_id: int, db: Session = Depends(get_db)):
    ms = EventOpsService.achieve_milestone(db, milestone_id)
    if not ms:
        raise HTTPException(404, "Milestone not found")
    return ms


# ── Resources ─────────────────────────────────────────────────────────────────

@router.post("/{event_id}/resources", response_model=ResourceOut, status_code=201)
def add_resource(event_id: int, data: ResourceCreate, db: Session = Depends(get_db)):
    if not EventOpsService.get_event(db, event_id):
        raise HTTPException(404, "Event not found")
    return EventOpsService.add_resource(db, event_id, data)


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.post("/{event_id}/notes", response_model=NoteOut, status_code=201)
def add_note(event_id: int, data: NoteCreate, db: Session = Depends(get_db)):
    if not EventOpsService.get_event(db, event_id):
        raise HTTPException(404, "Event not found")
    return EventOpsService.add_note(db, event_id, data)
'''

# =============================================================================
# ── SECTION 5: migrations/add_event_ops.py ───────────────────────────────────
# =============================================================================
EVENT_OPS_MIGRATION = '''
"""
migrations/add_event_ops.py
===========================
Alembic-compatible migration helper for Phase 5 Event Operations tables.

Usage (manual):
    python migrations/add_event_ops.py --create    # create tables
    python migrations/add_event_ops.py --drop      # drop tables (⚠ destructive)
    python migrations/add_event_ops.py --check     # verify tables exist
"""

import sys
import argparse

try:
    from app.database import engine, Base
except ImportError:
    from database import engine, Base

# Import models so Base.metadata sees them
from models.event_ops import (
    EvOps_Event, EvOps_Task, EvOps_Milestone,
    EvOps_Resource, EvOps_Note
)

TABLES = [
    "evops_events",
    "evops_tasks",
    "evops_milestones",
    "evops_resources",
    "evops_notes",
]


def create_tables():
    Base.metadata.create_all(bind=engine, tables=[
        Base.metadata.tables[t] for t in TABLES if t in Base.metadata.tables
    ])
    print("✅ Event Operations tables created:")
    for t in TABLES:
        print(f"   + {t}")


def drop_tables():
    confirm = input("⚠️  Drop ALL evops_* tables? Type YES to confirm: ")
    if confirm.strip() != "YES":
        print("Aborted.")
        return
    Base.metadata.drop_all(bind=engine, tables=[
        Base.metadata.tables[t] for t in TABLES if t in Base.metadata.tables
    ])
    print("🗑  Tables dropped.")


def check_tables():
    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing = inspector.get_table_names()
    print("Table presence check:")
    all_ok = True
    for t in TABLES:
        exists = t in existing
        print(f"  {'✅' if exists else '❌'}  {t}")
        if not exists:
            all_ok = False
    if all_ok:
        print("\\nAll Phase 5 tables are present.")
    else:
        print("\\nRun --create to add missing tables.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--drop",   action="store_true")
    parser.add_argument("--check",  action="store_true")
    args = parser.parse_args()

    if args.create:  create_tables()
    elif args.drop:  drop_tables()
    elif args.check: check_tables()
    else:
        parser.print_help()
        sys.exit(1)
'''

# =============================================================================
# ── SECTION 6: main.py snippet ───────────────────────────────────────────────
# =============================================================================
MAIN_SNIPPET = '''
# ── Add to your main.py ───────────────────────────────────────────────────────
# Place after your existing router includes.

from routers.event_ops_router import router as event_ops_router

app.include_router(
    event_ops_router,
    prefix="/api/v1/evops",
    tags=["Event Operations"],
)

# That's it. Available endpoints:
#   GET    /api/v1/evops/summary
#   GET    /api/v1/evops/stats
#   POST   /api/v1/evops/
#   GET    /api/v1/evops/{id}
#   GET    /api/v1/evops/pnr/{pnr_ref}
#   PATCH  /api/v1/evops/{id}
#   PATCH  /api/v1/evops/{id}/status
#   DELETE /api/v1/evops/{id}
#   POST   /api/v1/evops/{id}/tasks
#   PATCH  /api/v1/evops/tasks/{task_id}
#   DELETE /api/v1/evops/tasks/{task_id}
#   POST   /api/v1/evops/{id}/milestones
#   PATCH  /api/v1/evops/milestones/{id}/achieve
#   POST   /api/v1/evops/{id}/resources
#   POST   /api/v1/evops/{id}/notes
'''

# =============================================================================
# ── WRITER — splits this monolith into the actual files ──────────────────────
# =============================================================================
if __name__ == "__main__":
    import os

    SECTIONS = {
        "models/event_ops.py":              EVENT_OPS_MODELS,
        "schemas/event_ops.py":             EVENT_OPS_SCHEMAS,
        "services/event_ops.py":            EVENT_OPS_SERVICE,
        "routers/event_ops_router.py":      EVENT_OPS_ROUTER,
        "migrations/add_event_ops.py":      EVENT_OPS_MIGRATION,
        "_MAIN_SNIPPET.py":                 MAIN_SNIPPET,
    }

    print("Phase 5 — Event Operations Module Writer")
    print("=" * 45)
    for path, src in SECTIONS.items():
        dir_ = os.path.dirname(path)
        if dir_:
            os.makedirs(dir_, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(src.lstrip("\n"))
        print(f"  ✅  {path}  ({len(src.splitlines())} lines)")

    print()
    print("Next steps:")
    print("  1. python migrations/add_event_ops.py --create")
    print("  2. Paste contents of _MAIN_SNIPPET.py into main.py")
    print("  3. Restart server")
    print("  4. GET /api/v1/evops/summary → should return {total, active, items}")
