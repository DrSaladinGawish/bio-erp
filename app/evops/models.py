"""models.py — Event Operations ORM models"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean,
    Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


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
    __tablename__ = "evops_events"

    id              = Column(Integer, primary_key=True, index=True)
    pnr_ref         = Column(String(50), unique=True, index=True, nullable=False)
    title           = Column(String(200), nullable=False)
    description     = Column(Text, nullable=True)
    client_id       = Column(Integer, nullable=True)
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

    tasks      = relationship("EvOps_Task",      back_populates="event", cascade="all, delete-orphan")
    milestones = relationship("EvOps_Milestone",  back_populates="event", cascade="all, delete-orphan")
    resources  = relationship("EvOps_Resource",   back_populates="event", cascade="all, delete-orphan")
    notes      = relationship("EvOps_Note",       back_populates="event", cascade="all, delete-orphan")


class EvOps_Task(Base):
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
    __tablename__ = "evops_resources"

    id              = Column(Integer, primary_key=True, index=True)
    event_id        = Column(Integer, ForeignKey("evops_events.id"), nullable=False, index=True)
    resource_type   = Column(String(50), nullable=False)
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
    __tablename__ = "evops_notes"

    id          = Column(Integer, primary_key=True, index=True)
    event_id    = Column(Integer, ForeignKey("evops_events.id"), nullable=False, index=True)
    body        = Column(Text, nullable=False)
    author      = Column(String(100), nullable=True)
    is_internal = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    event       = relationship("EvOps_Event", back_populates="notes")
