# app/api/assignments.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.assignment import Assignment
from app.models.activity import Activity
from app.models.activity_schedule import ActivitySchedule
from app.schemas.assignment import (
    AssignmentProposeCreate,
    AssignmentSelfAssignCreate,
    AssignmentDecision,
    AssignmentOut,
    AssignmentsMineOut,
)
from app.services import assignments as svc

router = APIRouter(prefix="/assignments", tags=["assignments"])


def _to_out(db: Session, a: Assignment) -> AssignmentOut:
    user = db.query(User).filter(User.id == a.user_id).first()
    schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == a.activity_schedule_id).first()
    activity = db.query(Activity).filter(Activity.id == schedule.activity_id).first() if schedule else None

    return AssignmentOut(
        id=a.id,
        activity_schedule_id=a.activity_schedule_id,
        user_id=a.user_id,
        home_team_id=a.home_team_id,
        home_company_id=a.home_company_id,
        is_leader=a.is_leader,
        status=a.status,
        proposed_by=a.proposed_by,
        proposed_at=a.proposed_at,
        responded_at=a.responded_at,
        decline_reason=a.decline_reason,
        user_display_name=(user.display_name or user.email) if user else None,
        activity_title=activity.title if activity else None,
        schedule_start=schedule.start_time if schedule else None,
        schedule_end=schedule.end_time if schedule else None,
    )


@router.post("/propose", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def propose(
    payload: AssignmentProposeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        a = svc.propose_assignment(
            db,
            actor=current_user,
            activity_schedule_id=payload.activity_schedule_id,
            user_id=payload.user_id,
            is_leader=payload.is_leader,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(a)
    return _to_out(db, a)


@router.post("/self-assign", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def self_assign(
    payload: AssignmentSelfAssignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        a = svc.propose_assignment(
            db,
            actor=current_user,
            activity_schedule_id=payload.activity_schedule_id,
            user_id=current_user.id,
            is_leader=payload.is_leader,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(a)
    return _to_out(db, a)


@router.post("/{assignment_id}/respond", response_model=AssignmentOut)
def respond(
    assignment_id: UUID,
    payload: AssignmentDecision,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        a = svc.respond(
            db,
            assignment_id=assignment_id,
            actor=current_user,
            decision=payload.decision,
            decline_reason=payload.decline_reason,
        )
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(a)
    return _to_out(db, a)


@router.post("/{assignment_id}/cancel", response_model=AssignmentOut)
def cancel(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        a = svc.cancel_assignment(db, assignment_id=assignment_id, actor=current_user)
        db.commit()
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(a)
    return _to_out(db, a)


@router.get("/mine", response_model=AssignmentsMineOut)
def mine(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    incoming, mine_list = svc.list_for_user(db, current_user)
    return AssignmentsMineOut(
        incoming=[_to_out(db, a) for a in incoming],
        mine=[_to_out(db, a) for a in mine_list],
    )


@router.get("/schedule/{activity_schedule_id}", response_model=list[AssignmentOut])
def for_schedule(
    activity_schedule_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        assignments = svc.list_for_schedule(db, actor=current_user, activity_schedule_id=activity_schedule_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return [_to_out(db, a) for a in assignments]
