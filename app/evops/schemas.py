"""schemas.py — Pydantic v2 schemas for Event Operations"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

from app.evops.models import EventStatus, EventPriority, TaskStatus


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


class MilestoneCreate(BaseModel):
    name:        str = Field(..., min_length=1)
    target_date: datetime
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
    budget_utilization:float
    avg_task_completion:float
    upcoming_events:   int
