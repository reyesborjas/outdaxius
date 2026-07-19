# app/api/activity_schedules.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import uuid
from typing import List, Optional
from app.db.session import get_db
from app.models.activity_schedule import ActivitySchedule
from app.schemas.activity_schedule import ActivityScheduleCreate, ActivityScheduleOut
from app.api.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.program_schedule import ProgramSchedule
from app.models.programactivity import ProgramActivity
from app.models.activity import Activity
from app.models.team import Team
from app.core.permissions import require_action, check_can_reuse, get_user_team_membership
from app.services.enforce_limits import enforce_charges_enabled

router = APIRouter()

@router.get("/", response_model=List[ActivityScheduleOut])
def list_activity_schedules(
    db: Session = Depends(get_db),
    activity_id: uuid.UUID | None = None,
    mine_only: bool = False,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    q = db.query(ActivitySchedule)
    if activity_id:
        q = q.filter(ActivitySchedule.activity_id == activity_id)

    if mine_only:
        # See program_schedules.list_program_schedules -- same internal/back-office scoping,
        # doesn't affect the default public listing.
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required for mine_only")
        if current_user.role != "admin":
            membership = get_user_team_membership(db, current_user.id)
            if not membership:
                return []
            my_team = db.query(Team).filter(Team.id == membership.team_id).first()
            company_teams = db.query(Team.id).filter(Team.company_id == my_team.company_id).subquery()
            q = q.join(Activity, Activity.id == ActivitySchedule.activity_id).filter(
                Activity.team_id.in_(company_teams)
            )

    return q.distinct(ActivitySchedule.id).all()

@router.post("/", response_model=ActivityScheduleOut, status_code=status.HTTP_201_CREATED)
def create_activity_schedule(
    payload: ActivityScheduleCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_action("schedule.create"))
):
    if payload.program_schedule_id is None:
        # Standalone activity schedule -- resolve selling_company via the activity's own team.
        activity = db.query(Activity).filter(Activity.id == payload.activity_id).first()
        if not activity:
            raise HTTPException(404, "Activity not found")

        # Reuse policy: same team/company always allowed; a different company only if the
        # activity is marked is_shared.
        creator_membership = get_user_team_membership(db, current.id)
        creator_team_id = creator_membership.team_id if creator_membership else None
        if activity.team_id and creator_team_id and activity.team_id != creator_team_id:
            if not check_can_reuse(db, creator_team_id, activity.team_id, activity.is_shared):
                raise HTTPException(
                    status_code=403,
                    detail="This activity belongs to another company and is not marked as shared."
                )

        selling_company_id = None
        if activity.team_id:
            team = db.query(Team).filter(Team.id == activity.team_id).first()
            if team:
                selling_company_id = team.company_id
                enforce_charges_enabled(db, selling_company_id)

        sched = ActivitySchedule(**payload.model_dump(), selling_company_id=selling_company_id)
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

    # Inherits the parent program schedule's selling company -- already gated on charges_enabled
    # when the parent was created.
    sched = ActivitySchedule(**payload.model_dump(), selling_company_id=parent.selling_company_id)
    db.add(sched)
    db.commit()
    db.refresh(sched)
    return sched
