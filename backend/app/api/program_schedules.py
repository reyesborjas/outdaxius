# backend/app/api/program_schedules.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.programs import Program
from app.models.program_schedule import ProgramSchedule
from app.schemas.program_schedule import ProgramScheduleCreate, ProgramScheduleOut
from app.models.user import User
from typing import List
import uuid
from app.api.deps import get_current_company_id
from app.services.enforce_limits import enforce_company_creation_limits
from app.core.permissions import require_action

router = APIRouter()

@router.post("/", response_model=ProgramScheduleOut, status_code=201)
def create_program_schedule(
    payload: ProgramScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_action("schedule.create")),
    company_id = Depends(get_current_company_id),
):
    if company_id:
        enforce_company_creation_limits(db, company_id, metric="schedules_total")
        
    program = db.query(Program).get(payload.program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    sched = ProgramSchedule(
        program_id=payload.program_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        price=payload.price,
        status="pending",
    )
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched

@router.get("/", response_model=List[ProgramScheduleOut])
def list_program_schedules(
    db: Session = Depends(get_db),
    program_id: uuid.UUID | None = None
):
    q = db.query(ProgramSchedule)
    if program_id:
        q = q.filter(ProgramSchedule.program_id == program_id)
    return q.distinct(ProgramSchedule.id).all()
