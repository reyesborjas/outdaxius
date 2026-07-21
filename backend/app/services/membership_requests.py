# app/services/membership_requests.py
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.membership_request import MembershipRequest
from app.models.team import Team, TeamMember
from app.models.companymember import CompanyMember
from app.models.user import User
from app.core.permissions import check_team_or_company_admin, check_company_admin
from app.services.team_departure import get_departure_block_reason, remove_membership

DEFAULT_EXPIRES_DAYS = 14


def _expire_if_needed(db: Session, req: MembershipRequest) -> MembershipRequest:
    if req.status == "pending" and req.expires_at and req.expires_at < datetime.now(timezone.utc):
        req.status = "expired"
        db.flush()
    return req


def create_invitation(
    db: Session,
    *,
    team_id: UUID,
    created_by: User,
    target_user_id: Optional[UUID] = None,
    target_email: Optional[str] = None,
    offered_level: int = 4,
    message: Optional[str] = None,
    on_behalf_of_company_id: Optional[UUID] = None,
) -> MembershipRequest:
    if not target_user_id and not target_email:
        raise ValueError("target_user_id or target_email is required")
    if offered_level not in (1, 2, 3, 4):
        raise ValueError("offered_level must be between 1 and 4")

    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("Team not found")

    if on_behalf_of_company_id:
        # Three-party: an officer of the guide's OWN company proposes them for a different team.
        if not check_company_admin(db, created_by, on_behalf_of_company_id):
            raise ValueError("Only an admin of the guide's own company can propose them to another team")
        if not target_user_id:
            raise ValueError("Proposing on someone's behalf requires target_user_id")
        origin_membership = (
            db.query(TeamMember)
            .join(Team, Team.id == TeamMember.team_id)
            .filter(TeamMember.user_id == target_user_id, Team.company_id == on_behalf_of_company_id)
            .first()
        )
        if not origin_membership:
            raise ValueError("Target user is not currently on a team in that company")
        target_consent = "pending"
    else:
        if not check_team_or_company_admin(db, created_by, team_id):
            raise ValueError("Only the team's master guide or a company admin can invite members")
        target_consent = "not_required"

    existing_q = db.query(MembershipRequest).filter(
        MembershipRequest.team_id == team_id,
        MembershipRequest.status == "pending",
    )
    existing_q = (
        existing_q.filter(MembershipRequest.target_user_id == target_user_id)
        if target_user_id
        else existing_q.filter(MembershipRequest.target_email == target_email.lower())
    )
    if existing_q.first():
        raise ValueError("A pending request already exists for this person and team")

    req = MembershipRequest(
        direction="invitation",
        team_id=team_id,
        company_id=team.company_id,
        target_user_id=target_user_id,
        target_email=target_email.lower() if target_email else None,
        offered_level=offered_level,
        created_by=created_by.id,
        on_behalf_of_company_id=on_behalf_of_company_id,
        target_consent=target_consent,
        message=message,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=DEFAULT_EXPIRES_DAYS),
    )
    db.add(req)
    db.flush()
    return req


def create_application(
    db: Session,
    *,
    team_id: UUID,
    applicant: User,
    message: Optional[str] = None,
) -> MembershipRequest:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("Team not found")
    if applicant.role != "guide":
        raise ValueError("Only guides can apply to join a team")

    existing_membership = db.query(TeamMember).filter(TeamMember.user_id == applicant.id).first()
    if existing_membership and existing_membership.team_id == team_id:
        raise ValueError("You are already a member of this team")

    existing = db.query(MembershipRequest).filter(
        MembershipRequest.team_id == team_id,
        MembershipRequest.target_user_id == applicant.id,
        MembershipRequest.status == "pending",
    ).first()
    if existing:
        raise ValueError("You already have a pending request for this team")

    req = MembershipRequest(
        direction="application",
        team_id=team_id,
        company_id=team.company_id,
        target_user_id=applicant.id,
        offered_level=4,
        created_by=applicant.id,
        target_consent="not_required",
        message=message,
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=DEFAULT_EXPIRES_DAYS),
    )
    db.add(req)
    db.flush()
    return req


def consent(db: Session, *, request_id: UUID, user: User, decision: str) -> MembershipRequest:
    if decision not in ("granted", "refused"):
        raise ValueError("decision must be 'granted' or 'refused'")

    req = db.query(MembershipRequest).filter(MembershipRequest.id == request_id).first()
    if not req:
        raise ValueError("Request not found")
    _expire_if_needed(db, req)
    if req.status != "pending":
        raise ValueError(f"Request is {req.status}")
    if req.target_consent != "pending":
        raise ValueError("This request does not require consent")
    if req.target_user_id != user.id:
        raise ValueError("Only the proposed guide can respond to this request")

    req.target_consent = decision
    req.responded_at = datetime.now(timezone.utc)
    if decision == "refused":
        req.status = "rejected"
    db.flush()
    return req


def accept(db: Session, *, request_id: UUID, actor: User) -> MembershipRequest:
    req = db.query(MembershipRequest).filter(MembershipRequest.id == request_id).first()
    if not req:
        raise ValueError("Request not found")
    _expire_if_needed(db, req)
    if req.status != "pending":
        raise ValueError(f"Request is {req.status}")
    if req.target_consent == "pending":
        raise ValueError("Waiting on the proposed guide's consent before this can be accepted")
    if req.target_consent == "refused":
        raise ValueError("The proposed guide has refused this request")

    target_user_id = req.target_user_id
    if target_user_id is None:
        user = db.query(User).filter(User.email == req.target_email).first()
        if not user:
            raise ValueError("The invited person doesn't have an account yet")
        target_user_id = user.id
        req.target_user_id = target_user_id

    is_target = actor.id == target_user_id
    is_host = check_team_or_company_admin(db, actor, req.team_id)

    if req.direction == "invitation":
        if not (is_target or is_host):
            raise ValueError("Not authorized to accept this invitation")
    else:  # application
        if not is_host:
            raise ValueError("Only the team's master guide or a company admin can accept an application")

    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise ValueError("User not found")
    if target_user.role != "guide":
        raise ValueError("Only guides can join a team")

    existing_membership = db.query(TeamMember).filter(TeamMember.user_id == target_user_id).first()
    if existing_membership:
        if existing_membership.team_id == req.team_id:
            raise ValueError("Already a member of this team")
        block_reason = get_departure_block_reason(db, target_user, membership=existing_membership)
        if block_reason:
            raise ValueError(f"Cannot transfer: {block_reason}")
        remove_membership(db, existing_membership)

    db.add(TeamMember(team_id=req.team_id, user_id=target_user_id, role_level=req.offered_level))

    company_member = db.query(CompanyMember).filter(
        CompanyMember.companyid == req.company_id,
        CompanyMember.userid == target_user_id,
    ).first()
    if company_member:
        company_member.is_active = True
    else:
        db.add(CompanyMember(
            companyid=req.company_id,
            userid=target_user_id,
            position="Guide",
            is_admin=False,
            is_active=True,
            joinedat=datetime.now(timezone.utc).date(),
        ))

    req.status = "accepted"
    req.responded_at = datetime.now(timezone.utc)
    db.flush()
    return req


def reject(db: Session, *, request_id: UUID, actor: User) -> MembershipRequest:
    req = db.query(MembershipRequest).filter(MembershipRequest.id == request_id).first()
    if not req:
        raise ValueError("Request not found")
    _expire_if_needed(db, req)
    if req.status != "pending":
        raise ValueError(f"Request is {req.status}")

    is_target = actor.id == req.target_user_id or (
        req.target_email and actor.email.lower() == req.target_email.lower()
    )
    is_host = check_team_or_company_admin(db, actor, req.team_id)
    if not (is_target or is_host):
        raise ValueError("Not authorized to reject this request")

    req.status = "rejected"
    req.responded_at = datetime.now(timezone.utc)
    db.flush()
    return req


def cancel(db: Session, *, request_id: UUID, actor: User) -> MembershipRequest:
    req = db.query(MembershipRequest).filter(MembershipRequest.id == request_id).first()
    if not req:
        raise ValueError("Request not found")
    if req.created_by != actor.id:
        raise ValueError("Only the creator can cancel this request")
    if req.status != "pending":
        raise ValueError(f"Request is {req.status}, cannot cancel")
    req.status = "cancelled"
    req.responded_at = datetime.now(timezone.utc)
    db.flush()
    return req


def list_for_user(db: Session, *, user: User):
    """
    Returns (incoming, outgoing, team_pending) for this user:
      - incoming: pending requests targeting them (by user id or email) needing their action
        (accept/decline an invitation, or grant/refuse consent)
      - outgoing: requests they created, any status
      - team_pending: pending requests for teams they have host authority over (accept/reject)
    """
    incoming = db.query(MembershipRequest).filter(
        MembershipRequest.status == "pending",
        (MembershipRequest.target_user_id == user.id)
        | (MembershipRequest.target_email == user.email.lower()),
    ).all()

    outgoing = db.query(MembershipRequest).filter(MembershipRequest.created_by == user.id).all()

    my_team_ids = [
        t.team_id for t in db.query(TeamMember.team_id).filter(
            TeamMember.user_id == user.id, TeamMember.role_level == 1
        ).all()
    ]
    my_admin_company_ids = [
        c.companyid for c in db.query(CompanyMember.companyid).filter(
            CompanyMember.userid == user.id, CompanyMember.is_admin == True, CompanyMember.is_active == True  # noqa: E712
        ).all()
    ]
    team_pending = []
    scope_conditions = []
    if my_team_ids:
        scope_conditions.append(MembershipRequest.team_id.in_(my_team_ids))
    if my_admin_company_ids:
        scope_conditions.append(MembershipRequest.company_id.in_(my_admin_company_ids))
    if scope_conditions:
        team_pending = db.query(MembershipRequest).filter(
            MembershipRequest.status == "pending",
            or_(*scope_conditions),
        ).all()

    for req in incoming + outgoing + team_pending:
        _expire_if_needed(db, req)

    return incoming, outgoing, team_pending
