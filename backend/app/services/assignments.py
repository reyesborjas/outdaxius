# app/services/assignments.py
"""
Assignment lifecycle (Phase 6.1, spec 1.6): which guide executes an activity schedule, and
schedule-conflict detection. Two entry points into propose_assignment(): a team leader (role_level
<= 2) proposing ANY guide, or that same leader self-assigning (actor.id == user_id), which
auto-accepts since no separate consent step is meaningful when you're the one proposing yourself.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.assignment import Assignment
from app.models.activity import Activity
from app.models.activity_schedule import ActivitySchedule
from app.models.team import Team
from app.models.user import User
from app.core.permissions import check_permission, check_can_be_assigned, get_user_team_membership


def _can_manage_schedule_staffing(db: Session, actor: User, activity: Activity) -> bool:
    """Who may propose/cancel assignments for a schedule: leadership (role_level <= 2) of the
    activity's own team, matching the rest of the codebase's team-scoped authorization. Teamless
    activities (see the 2026-07-19 orphaned-content fix) fall back to creator-or-admin, same as
    check_permission_for_resource."""
    if activity.team_id is None:
        return actor.role == "admin" or actor.id == activity.created_by
    return check_permission(db, actor, "assignment.self_assign", team_id=activity.team_id)


def check_schedule_conflict(
    db: Session,
    user_id: UUID,
    schedule: ActivitySchedule,
    exclude_assignment_id: Optional[UUID] = None,
) -> Optional[Assignment]:
    """Only CONFIRMED (accepted) assignments count as a conflict -- a still-pending proposal on
    another schedule isn't a real commitment yet."""
    q = (
        db.query(Assignment)
        .join(ActivitySchedule, ActivitySchedule.id == Assignment.activity_schedule_id)
        .filter(
            Assignment.user_id == user_id,
            Assignment.status == "accepted",
            Assignment.activity_schedule_id != schedule.id,
            ActivitySchedule.start_time < schedule.end_time,
            ActivitySchedule.end_time > schedule.start_time,
        )
    )
    if exclude_assignment_id:
        q = q.filter(Assignment.id != exclude_assignment_id)
    return q.first()


def propose_assignment(
    db: Session,
    *,
    actor: User,
    activity_schedule_id: UUID,
    user_id: UUID,
    is_leader: bool = False,
) -> Assignment:
    schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == activity_schedule_id).first()
    if not schedule:
        raise ValueError("Activity schedule not found")
    activity = db.query(Activity).filter(Activity.id == schedule.activity_id).first()
    if not activity:
        raise ValueError("Activity not found")

    if not _can_manage_schedule_staffing(db, actor, activity):
        raise ValueError("Insufficient authority to staff this schedule")

    target_membership = get_user_team_membership(db, user_id)
    if not target_membership:
        raise ValueError("User has no team membership")

    if not check_can_be_assigned(db, user_id, activity_schedule_id):
        raise ValueError(
            "A field guide (role_level 4) cannot be assigned to a schedule that belongs to a program"
        )

    # uq_assignment_once is unconditional (schedule, user), not scoped by status -- a previously
    # rejected/cancelled row must be re-used in place rather than inserted again.
    existing = (
        db.query(Assignment)
        .filter(
            Assignment.activity_schedule_id == activity_schedule_id,
            Assignment.user_id == user_id,
        )
        .first()
    )
    if existing and existing.status in ("proposed", "accepted"):
        raise ValueError(f"An assignment already exists for this user on this schedule ({existing.status})")

    if is_leader:
        current_leader = (
            db.query(Assignment)
            .filter(
                Assignment.activity_schedule_id == activity_schedule_id,
                Assignment.is_leader == True,  # noqa: E712
                Assignment.status.in_(("proposed", "accepted")),
            )
            .first()
        )
        if current_leader:
            raise ValueError("This schedule already has a proposed or accepted leader")

    is_self = actor.id == user_id
    if check_schedule_conflict(db, user_id, schedule):
        raise ValueError("This guide already has a confirmed assignment overlapping this time window")

    team = db.query(Team).filter(Team.id == target_membership.team_id).first()
    now = datetime.now(timezone.utc)
    status = "accepted" if is_self else "proposed"

    if existing:
        existing.home_team_id = target_membership.team_id
        existing.home_company_id = team.company_id
        existing.is_leader = is_leader
        existing.status = status
        existing.proposed_by = actor.id
        existing.proposed_at = now
        existing.responded_at = now if is_self else None
        existing.decline_reason = None
        db.flush()
        return existing

    assignment = Assignment(
        activity_schedule_id=activity_schedule_id,
        user_id=user_id,
        home_team_id=target_membership.team_id,
        home_company_id=team.company_id,
        is_leader=is_leader,
        proposed_by=actor.id,
        status=status,
        responded_at=now if is_self else None,
    )
    db.add(assignment)
    db.flush()
    return assignment


def respond(
    db: Session,
    *,
    assignment_id: UUID,
    actor: User,
    decision: str,
    decline_reason: Optional[str] = None,
) -> Assignment:
    if decision not in ("accept", "decline"):
        raise ValueError("decision must be 'accept' or 'decline'")

    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise ValueError("Assignment not found")
    if a.user_id != actor.id:
        raise ValueError("Only the proposed guide can respond to this assignment")
    if a.status != "proposed":
        raise ValueError(f"Assignment is {a.status}")

    if decision == "accept":
        schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == a.activity_schedule_id).first()
        if check_schedule_conflict(db, a.user_id, schedule, exclude_assignment_id=a.id):
            raise ValueError("You already have a confirmed assignment overlapping this time window")
        a.status = "accepted"
    else:
        a.status = "rejected"
        a.decline_reason = decline_reason

    a.responded_at = datetime.now(timezone.utc)
    db.flush()
    return a


def cancel_assignment(db: Session, *, assignment_id: UUID, actor: User) -> Assignment:
    a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not a:
        raise ValueError("Assignment not found")
    if a.status not in ("proposed", "accepted"):
        raise ValueError(f"Assignment is already {a.status}")

    schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == a.activity_schedule_id).first()
    activity = db.query(Activity).filter(Activity.id == schedule.activity_id).first() if schedule else None

    is_assignee = actor.id == a.user_id
    is_staffer = activity is not None and _can_manage_schedule_staffing(db, actor, activity)
    if not (is_assignee or is_staffer):
        raise ValueError("Not authorized to cancel this assignment")

    a.status = "cancelled"
    a.responded_at = datetime.now(timezone.utc)
    db.flush()
    return a


def list_for_user(db: Session, user: User) -> tuple[list[Assignment], list[Assignment]]:
    """Returns (incoming, mine): incoming = pending proposals awaiting this user's accept/decline,
    mine = every assignment ever tied to this user regardless of status."""
    incoming = (
        db.query(Assignment)
        .filter(Assignment.user_id == user.id, Assignment.status == "proposed")
        .all()
    )
    mine = db.query(Assignment).filter(Assignment.user_id == user.id).all()
    return incoming, mine


def list_for_schedule(db: Session, *, actor: User, activity_schedule_id: UUID) -> list[Assignment]:
    schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == activity_schedule_id).first()
    if not schedule:
        raise ValueError("Activity schedule not found")
    activity = db.query(Activity).filter(Activity.id == schedule.activity_id).first()

    assignments = (
        db.query(Assignment).filter(Assignment.activity_schedule_id == activity_schedule_id).all()
    )

    if actor.role == "admin" or (activity is not None and _can_manage_schedule_staffing(db, actor, activity)):
        return assignments
    if any(a.user_id == actor.id for a in assignments):
        return assignments
    raise ValueError("Not authorized to view this schedule's assignments")
