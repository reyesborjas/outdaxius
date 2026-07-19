# app/core/permissions.py
"""
Centralized authorisation.

Two independent axes, per the Outdaxius spec — never conflate them:
  - COMMERCIAL authority: company_members.is_admin (billing, licensing, creating teams, hiring,
    invitations). The holder need not be a guide at all.
  - OPERATIONAL authority: team_members.role_level, 1 (most power) to 4 (least). Cascading: every
    capability held at level N is also held by every level below N, so the whole check reduces to
    a single comparison, user_level <= required_level.

check_company_admin() and check_permission()/check_team_or_company_admin() intentionally never
call into each other's underlying table for the *authority* decision — company.py and
companymember.py should use check_company_admin for commercial actions (creating a team, managing
company_members), while programs/activities/schedules use check_permission for operational
actions. check_team_or_company_admin is the one deliberate bridge: managing a specific team's
membership is allowed by either axis, because a company officer must be able to manage a team's
roster even if they never personally joined that team as a guide.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.team import Team, TeamMember
from app.models.companymember import CompanyMember


# Minimum role_level (maximum required "power") for each operational action. A caller with
# role_level <= this value is permitted; a HIGHER number means LESS authority, per the spec's
# cascading hierarchy (1 master .. 4 field guide).
ACTION_LEVELS = {
    "program.create": 1,
    "program.edit": 2,
    "program.delete": 1,
    "activity.create": 3,
    "activity.edit": 3,
    "activity.delete": 1,
    "schedule.create": 2,
    "schedule.edit": 3,
    "schedule.cancel": 2,
    # Spec: "Only if unbooked" for level 1 specifically — callers must ALSO check for existing
    # bookings before allowing this; this constant only encodes the role_level half of the rule.
    "schedule.hard_delete": 1,
    "assignment.self_assign": 2,
    # Every level, including 4, may accept or decline an assignment already proposed to them.
    "assignment.accept_decline": 4,
    "team.manage_membership": 1,
}


def get_user_team_membership(db: Session, user_id: UUID) -> Optional[TeamMember]:
    """Membership is exclusive (Phase 2's uq_team_members_user) — at most one row, ever."""
    return db.query(TeamMember).filter(TeamMember.user_id == user_id).first()


def check_permission(
    db: Session,
    user: User,
    action: str,
    team_id: Optional[UUID] = None,
) -> bool:
    """
    Operational-axis check. Platform admin always passes. Otherwise the caller must be a member
    of the team that owns the resource (when team_id is given) with sufficient role_level.

    team_id=None is only appropriate for actions where the caller's own membership IS the team in
    question (e.g. "can this user create a program at all" before the program exists) — never for
    editing/deleting an existing resource, where the resource's actual team_id must be passed so a
    master of team A can't act on team B's resources.
    """
    if user.role == "admin":
        return True

    required_level = ACTION_LEVELS.get(action)
    if required_level is None:
        raise ValueError(f"Unknown permission action: {action}")

    membership = get_user_team_membership(db, user.id)
    if membership is None:
        return False

    if team_id is not None and membership.team_id != team_id:
        return False

    return membership.role_level <= required_level


def check_permission_for_resource(
    db: Session,
    user: User,
    action: str,
    team_id: Optional[UUID],
    created_by: UUID,
) -> bool:
    """
    Like check_permission, but for editing/deleting an EXISTING resource that may have no
    owning team (team_id is None -- orphaned legacy content; see the 2026-07-19 production
    incident where content created by a teamless user, notably platform admins, ended up with
    no team_id at all). A None team_id must never fall through to check_permission's
    "no team constraint" branch -- that branch exists only for pre-creation checks, per its own
    docstring. An ownerless resource may only be touched by its original creator or a platform
    admin, never by an arbitrary team member elsewhere who happens to have sufficient role_level.
    """
    if team_id is None:
        return user.role == "admin" or user.id == created_by
    return check_permission(db, user, action, team_id=team_id)


def require_action(action: str):
    """
    FastAPI dependency for CREATE endpoints, where the resource will belong to the caller's own
    team (team_id is resolved from the caller's membership, not a path/body parameter). Raises 403
    rather than returning False, since this is meant to sit directly in a route signature.
    """

    def dependency(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        if not check_permission(db, current_user, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role_level for: {action}",
            )
        return current_user

    return dependency


def check_company_admin(db: Session, user: User, company_id: UUID) -> bool:
    """
    Commercial-axis check only: platform admin, or an active is_admin company_members row for
    this company. Deliberately does not look at team_members/role_level at all.
    """
    if user.role == "admin":
        return True
    member = (
        db.query(CompanyMember)
        .filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == user.id,
            CompanyMember.is_admin == True,  # noqa: E712
            CompanyMember.is_active == True,  # noqa: E712
        )
        .first()
    )
    return member is not None


def check_company_member(db: Session, user: User, company_id: UUID) -> bool:
    """Commercial-axis visibility check: platform admin, or any active company_members row
    (not necessarily is_admin) for this company."""
    if user.role == "admin":
        return True
    member = (
        db.query(CompanyMember)
        .filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == user.id,
            CompanyMember.is_active == True,  # noqa: E712
        )
        .first()
    )
    return member is not None


def check_team_or_company_admin(db: Session, user: User, team_id: UUID) -> bool:
    """
    The one deliberate bridge between the two axes: managing a specific team's roster is allowed
    by EITHER being that team's own master guide (role_level 1) OR being a commercial admin of the
    company that owns the team. Closes the gap where a company officer who didn't personally join
    a team as a guide was locked out of managing it.
    """
    if user.role == "admin":
        return True

    membership = db.query(TeamMember).filter(
        TeamMember.user_id == user.id,
        TeamMember.team_id == team_id,
    ).first()
    if membership is not None and membership.role_level == 1:
        return True

    team = db.query(Team).filter(Team.id == team_id).first()
    if team is None:
        return False
    return check_company_admin(db, user, team.company_id)


def check_can_reuse(
    db: Session,
    creator_team_id: Optional[UUID],
    owner_team_id: Optional[UUID],
    is_shared: bool,
) -> bool:
    """
    Reuse policy for scheduling someone else's activity/program: the caller's own team may
    always schedule it. Any team in the SAME company may always schedule it too. A team in a
    DIFFERENT company may only schedule it when the resource is explicitly marked is_shared.
    """
    if not creator_team_id or not owner_team_id:
        return False
    if creator_team_id == owner_team_id:
        return True

    creator_team = db.query(Team).filter(Team.id == creator_team_id).first()
    owner_team = db.query(Team).filter(Team.id == owner_team_id).first()
    if not creator_team or not owner_team:
        return False
    if creator_team.company_id == owner_team.company_id:
        return True

    return bool(is_shared)


def check_can_be_assigned(db: Session, user_id: UUID, activity_schedule_id: UUID) -> bool:
    """
    Spec 1.6: a role_level 4 (field) guide may lead/participate in a standalone activity when
    assigned, but is NEVER assigned to an activity schedule that belongs to a program.

    Not currently called from any live endpoint — there is no assignment-creation API yet (the
    `assignments` table is new as of the Phase 2 migration). Ready for whichever future phase adds
    that endpoint.
    """
    from app.models.activity_schedule import ActivitySchedule  # local import: avoid a cycle

    membership = get_user_team_membership(db, user_id)
    if membership is None:
        return False

    schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == activity_schedule_id).first()
    if schedule is not None and schedule.program_schedule_id is not None and membership.role_level == 4:
        return False

    return True
