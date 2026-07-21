# app/services/team_departure.py
"""
Spec 1.7 departure guard. Because team membership is exclusive, leaving a team is a transfer,
not a delete -- see Table 5 in the spec:
  - level 2-4, no future confirmed leadership: free to leave
  - level 2-4, leading a future confirmed schedule: blocked until reassigned
  - level 1, team has other members: blocked until a successor is promoted to level 1
  - level 1, team otherwise empty: allowed, and the team is archived (is_active=False)
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember
from app.models.activity import Activity
from app.models.programs import Program
from app.models.activity_schedule import ActivitySchedule
from app.models.program_schedule import ProgramSchedule
from app.models.user import User


def get_departure_block_reason(
    db: Session,
    user: User,
    membership: Optional[TeamMember] = None,
) -> Optional[str]:
    """Returns a human-readable block reason, or None if free to leave/transfer. Read-only."""
    membership = membership or db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
    if membership is None:
        return None  # not on a team; nothing to guard

    if membership.role_level == 1:
        other_members = db.query(TeamMember).filter(
            TeamMember.team_id == membership.team_id,
            TeamMember.id != membership.id,
        ).count()
        if other_members > 0:
            return "You are the team's master guide; promote a successor to level 1 before leaving."
        return None

    now = datetime.now(timezone.utc)
    leads_activity_ids = db.query(Activity.id).filter(Activity.guide_leader == user.id).scalar_subquery()
    leads_program_ids = db.query(Program.id).filter(Program.guide_leader == user.id).scalar_subquery()

    future_activity_schedule = db.query(ActivitySchedule).filter(
        ActivitySchedule.activity_id.in_(leads_activity_ids),
        ActivitySchedule.status == "confirmed",
        ActivitySchedule.start_time > now,
    ).first()
    if future_activity_schedule:
        return "You lead a future confirmed activity schedule; reassign it before leaving."

    future_program_schedule = db.query(ProgramSchedule).filter(
        ProgramSchedule.program_id.in_(leads_program_ids),
        ProgramSchedule.status == "confirmed",
        ProgramSchedule.start_time > now,
    ).first()
    if future_program_schedule:
        return "You lead a future confirmed program schedule; reassign it before leaving."

    return None


def remove_membership(db: Session, membership: TeamMember) -> None:
    """
    Deletes a team_members row, archiving the team first if this was its last member --
    shared by leave_team() below and membership_requests.accept() (which also removes an
    existing membership when transferring someone into a different team).
    """
    other_members = db.query(TeamMember).filter(
        TeamMember.team_id == membership.team_id,
        TeamMember.id != membership.id,
    ).count()
    if other_members == 0:
        team = db.query(Team).filter(Team.id == membership.team_id).first()
        if team:
            team.is_active = False
    db.delete(membership)
    db.flush()


def leave_team(db: Session, user: User) -> None:
    membership = db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
    if membership is None:
        raise ValueError("You are not currently on a team")
    reason = get_departure_block_reason(db, user, membership=membership)
    if reason:
        raise ValueError(reason)
    remove_membership(db, membership)
