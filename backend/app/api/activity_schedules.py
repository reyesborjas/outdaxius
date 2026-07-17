# app/api/activity_schedules.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from typing import List
from app.db.session import get_db
from app.models.activity_schedule import ActivitySchedule
from app.schemas.activity_schedule import ActivityScheduleCreate, ActivityScheduleOut
from app.api.deps import get_current_user
from app.models.user import User
from app.models.program_schedule import ProgramSchedule
from app.models.programactivity import ProgramActivity

router = APIRouter()

@router.get("/", response_model=List[ActivityScheduleOut])
def list_activity_schedules(
    db: Session = Depends(get_db),
    activity_id: uuid.UUID | None = None
):
    q = db.query(ActivitySchedule)
    if activity_id:
        q = q.filter(ActivitySchedule.activity_id == activity_id)
    return q.distinct(ActivitySchedule.id).all()

@router.post("/", response_model=ActivityScheduleOut, status_code=status.HTTP_201_CREATED)
def create_activity_schedule(
    payload: ActivityScheduleCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user)
):
    if payload.program_schedule_id is None:
        sched = ActivitySchedule(**payload.model_dump())
        db.add(sched)
        db.commit()
        db.refresh(sched)
        return sched

    parent = db.query(ProgramSchedule).filter(ProgramSchedule.id == payload.program_schedule_id).first()
    if not parent:
        raise HTTPException(404, "Parent program schedule not found")

    exists = db.query(ProgramActivity).filter(
        ProgramActivity.program_id == parent.program_id,
        ProgramActivity.activity_id == payload.activity_id
    ).first()
    if not exists:
        raise HTTPException(400, "Activity is not part of the parent program")

    if not (parent.start_time <= payload.start_time <= parent.end_time and
            parent.start_time <= payload.end_time <= parent.end_time):
        raise HTTPException(400, "Activity schedule must be inside program schedule window")

    sched = ActivitySchedule(**payload.model_dump())
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched
