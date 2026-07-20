# app/services/personal_team.py
"""
Every guide is meant to always hold exactly one team_members row -- "teamless guide" must not be
a reachable state. It was, historically (see the 2026-07-19 production incident: platform admins
and a handful of guides created content with no team at all, silently defeating the cross-company
reuse policy for every one of those programs/activities). Admins are exempt: they're platform
super-users, not commercial actors, and the two-axis permission model already gives them universal
access without needing a team of their own.

This auto-creates a minimal PERSONAL company (named after the guide, no real legal/business
info -- see the 0004_company_nullable_legal_fields migration) and a team of one inside it, with
the guide as its level-1 (master) member. It is deliberately NOT a replacement for the real
"Create Company" flow -- a guide can still build or join an actual multi-person company later
(including via the membership_requests invite/apply flow), at which point their personal team is
just left behind (team-of-one departures are always unblocked by the departure guard).
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.company import Company
from app.models.companymember import CompanyMember
from app.models.team import Team, TeamMember


def ensure_personal_team(db: Session, user: User) -> TeamMember:
    """Idempotent: no-ops if the user already holds a team_members row."""
    existing = db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
    if existing is not None:
        return existing

    company = Company(
        name=user.display_name,
        createdby=user.id,
        is_multinational=False,
        license_tier="free",
        is_active=True,
    )
    db.add(company)
    db.flush()

    db.add(CompanyMember(
        companyid=company.id,
        userid=user.id,
        position="Owner",
        is_admin=True,
        is_active=True,
        joinedat=datetime.now(timezone.utc).date(),
    ))

    team = Team(
        name=f"{user.display_name}'s Team",
        created_by=user.id,
        company_id=company.id,
    )
    db.add(team)
    db.flush()

    member = TeamMember(team_id=team.id, user_id=user.id, role_level=1)
    db.add(member)
    db.flush()
    return member
