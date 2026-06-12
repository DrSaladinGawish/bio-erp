"""router.py — FastAPI router for Event Operations (Phase 5)"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_sync_session
from app.evops.models import EventStatus, EventPriority
from app.evops.schemas import (
    EventCreate, EventUpdate, EventDetail, EventSummary,
    EventListResponse, EventStatsResponse,
    TaskCreate, TaskUpdate, TaskOut,
    MilestoneCreate, MilestoneOut,
    ResourceCreate, ResourceOut,
    NoteCreate, NoteOut,
)
from app.evops.service import EventOpsService


def get_sync_db():
    db = get_sync_session()
    try:
        yield db
    finally:
        db.close()


router = APIRouter()


@router.get("/summary", response_model=EventListResponse)
def list_events(
    status_filter: Optional[EventStatus] = None,
    event_type: Optional[str] = None,
    client_id: Optional[int] = None,
    active_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_sync_db),
):
    total, active, items = EventOpsService.list_events(
        db, status_filter, event_type, client_id, active_only, skip, limit
    )
    return {"total": total, "active": active, "items": items}


@router.get("/stats", response_model=EventStatsResponse)
def event_stats(db: Session = Depends(get_sync_db)):
    return EventOpsService.get_stats(db)


@router.post("/", response_model=EventDetail, status_code=status.HTTP_201_CREATED)
def create_event(data: EventCreate, db: Session = Depends(get_sync_db)):
    if EventOpsService.get_event_by_pnr(db, data.pnr_ref):
        raise HTTPException(409, f"PNR '{data.pnr_ref}' already exists")
    return EventOpsService.create_event(db, data)


@router.get("/{event_id}", response_model=EventDetail)
def get_event(event_id: int, db: Session = Depends(get_sync_db)):
    ev = EventOpsService.get_event(db, event_id)
    if not ev:
        raise HTTPException(404, "Event not found")
    ev.task_count = len(ev.tasks)
    ev.tasks_done = sum(1 for t in ev.tasks if t.status.value == "done")
    return ev


@router.get("/pnr/{pnr_ref}", response_model=EventDetail)
def get_event_by_pnr(pnr_ref: str, db: Session = Depends(get_sync_db)):
    ev = EventOpsService.get_event_by_pnr(db, pnr_ref)
    if not ev:
        raise HTTPException(404, f"PNR '{pnr_ref}' not found")
    return ev


@router.patch("/{event_id}", response_model=EventDetail)
def update_event(event_id: int, data: EventUpdate, db: Session = Depends(get_sync_db)):
    ev = EventOpsService.update_event(db, event_id, data)
    if not ev:
        raise HTTPException(404, "Event not found")
    return ev


@router.patch("/{event_id}/status", response_model=EventDetail)
def transition_status(
    event_id: int,
    new_status: EventStatus,
    db: Session = Depends(get_sync_db),
):
    try:
        ev = EventOpsService.transition_status(db, event_id, new_status)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not ev:
        raise HTTPException(404, "Event not found")
    return ev


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def soft_delete_event(event_id: int, db: Session = Depends(get_sync_db)):
    if not EventOpsService.delete_event(db, event_id):
        raise HTTPException(404, "Event not found")


@router.post("/{event_id}/tasks", response_model=TaskOut, status_code=201)
def add_task(event_id: int, data: TaskCreate, db: Session = Depends(get_sync_db)):
    if not EventOpsService.get_event(db, event_id):
        raise HTTPException(404, "Event not found")
    return EventOpsService.add_task(db, event_id, data)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, data: TaskUpdate, db: Session = Depends(get_sync_db)):
    task = EventOpsService.update_task(db, task_id, data)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_sync_db)):
    if not EventOpsService.delete_task(db, task_id):
        raise HTTPException(404, "Task not found")


@router.post("/{event_id}/milestones", response_model=MilestoneOut, status_code=201)
def add_milestone(event_id: int, data: MilestoneCreate, db: Session = Depends(get_sync_db)):
    if not EventOpsService.get_event(db, event_id):
        raise HTTPException(404, "Event not found")
    return EventOpsService.add_milestone(db, event_id, data)


@router.patch("/milestones/{milestone_id}/achieve", response_model=MilestoneOut)
def achieve_milestone(milestone_id: int, db: Session = Depends(get_sync_db)):
    ms = EventOpsService.achieve_milestone(db, milestone_id)
    if not ms:
        raise HTTPException(404, "Milestone not found")
    return ms


@router.post("/{event_id}/resources", response_model=ResourceOut, status_code=201)
def add_resource(event_id: int, data: ResourceCreate, db: Session = Depends(get_sync_db)):
    if not EventOpsService.get_event(db, event_id):
        raise HTTPException(404, "Event not found")
    return EventOpsService.add_resource(db, event_id, data)


@router.post("/{event_id}/notes", response_model=NoteOut, status_code=201)
def add_note(event_id: int, data: NoteCreate, db: Session = Depends(get_sync_db)):
    if not EventOpsService.get_event(db, event_id):
        raise HTTPException(404, "Event not found")
    return EventOpsService.add_note(db, event_id, data)
