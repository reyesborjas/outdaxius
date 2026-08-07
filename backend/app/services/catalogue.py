# backend/app/services/catalogue.py
"""
Who may see which activities and programs.

The catalogue endpoints used to return every row on the platform to every caller, authenticated
or not, including other companies' private (is_shared=false) content. The write path was already
correct -- app.core.permissions.check_can_reuse refuses to schedule another company's non-shared
resource -- so the listing was a disclosure, and it also misled the UI into offering actions the
API would then reject with 403.

There are two audiences, and they cannot share one filter. SearchActivities/SearchPrograms/
SearchTrips are customer-facing, so scoping the single listing to team members would leave
travellers with nothing to browse.

  PUBLIC (default)    what a traveller may discover: offerings with a real, bookable departure.
                      Plus, for a signed-in caller, anything they have already booked -- so their
                      own trip history keeps resolving after a departure has passed.

  INTERNAL (mine_only) what a guide picks from when scheduling: their own company's catalogue plus
                      anything explicitly shared. Deliberately mirrors check_can_reuse, so the
                      list offers exactly what the write path will accept.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy.sql.elements import ColumnElement

from app.models.activity import Activity
from app.models.activity_schedule import ActivitySchedule
from app.models.booking import Booking
from app.models.company_payment_account import CompanyPaymentAccount
from app.models.program_schedule import ProgramSchedule
from app.models.programs import Program
from app.models.team import Team, TeamMember
from app.models.user import User

# Schedule status values are "pending | confirmed | canceled" (one L -- see
# app.models.activity_schedule). Both pending and confirmed departures are offered publicly; a
# pending departure is one still gathering its minimum group, which is exactly the thing a
# traveller needs to be able to find and join.
_LIVE_SCHEDULE_STATUSES = ("pending", "confirmed")


def _sellable_activity_ids() -> Select:
    """Activities with at least one upcoming, non-cancelled departure whose selling company can
    actually take money (company_payment_accounts.charges_enabled).

    Child schedules of a program are intentionally included: they carry a real selling company and
    are bookable rows in their own right, and excluding them would hide activities that only ever
    run as part of a program.
    """
    return (
        select(ActivitySchedule.activity_id)
        .join(
            CompanyPaymentAccount,
            CompanyPaymentAccount.company_id == ActivitySchedule.selling_company_id,
        )
        .where(
            CompanyPaymentAccount.charges_enabled.is_(True),
            ActivitySchedule.status.in_(_LIVE_SCHEDULE_STATUSES),
            ActivitySchedule.start_time >= func.now(),
        )
        .distinct()
    )


def _sellable_program_ids() -> Select:
    return (
        select(ProgramSchedule.program_id)
        .join(
            CompanyPaymentAccount,
            CompanyPaymentAccount.company_id == ProgramSchedule.selling_company_id,
        )
        .where(
            CompanyPaymentAccount.charges_enabled.is_(True),
            ProgramSchedule.status.in_(_LIVE_SCHEDULE_STATUSES),
            ProgramSchedule.start_time >= func.now(),
        )
        .distinct()
    )


def _booked_activity_ids(viewer: User) -> Select:
    return (
        select(ActivitySchedule.activity_id)
        .join(Booking, Booking.activity_schedule_id == ActivitySchedule.id)
        .where(Booking.user_id == viewer.id)
        .distinct()
    )


def _booked_program_ids(viewer: User) -> Select:
    return (
        select(ProgramSchedule.program_id)
        .join(Booking, Booking.program_schedule_id == ProgramSchedule.id)
        .where(Booking.user_id == viewer.id)
        .distinct()
    )


def _my_company_team_ids(db: Session, user: User) -> Optional[Select]:
    """Every team belonging to the company `user` is a member of, or None if they have no team.

    Company-wide rather than team-only, matching check_can_reuse: any team in the same company may
    schedule a sibling team's resource.
    """
    membership = db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
    if not membership:
        return None
    team = db.query(Team).filter(Team.id == membership.team_id).first()
    if not team or not team.company_id:
        return None
    return select(Team.id).where(Team.company_id == team.company_id)


# --- public -------------------------------------------------------------------------------
def public_activity_filter(viewer: Optional[User]) -> ColumnElement[bool]:
    sellable = Activity.id.in_(_sellable_activity_ids())
    if viewer is None:
        return sellable
    return or_(sellable, Activity.id.in_(_booked_activity_ids(viewer)))


def public_program_filter(viewer: Optional[User]) -> ColumnElement[bool]:
    sellable = Program.id.in_(_sellable_program_ids())
    if viewer is None:
        return sellable
    return or_(sellable, Program.id.in_(_booked_program_ids(viewer)))


# --- internal -----------------------------------------------------------------------------
def internal_activity_filter(db: Session, user: User) -> ColumnElement[bool]:
    """The caller's own company's activities, plus anything explicitly shared."""
    team_ids = _my_company_team_ids(db, user)
    if team_ids is None:
        # An unaffiliated guide has no company catalogue of their own; they may still schedule
        # shared resources, so those are what they should be offered.
        return Activity.is_shared.is_(True)
    return or_(Activity.is_shared.is_(True), Activity.team_id.in_(team_ids))


def internal_program_filter(db: Session, user: User) -> ColumnElement[bool]:
    team_ids = _my_company_team_ids(db, user)
    if team_ids is None:
        return Program.is_shared.is_(True)
    return or_(Program.is_shared.is_(True), Program.team_id.in_(team_ids))


# --- entry points used by the routes -------------------------------------------------------
def activity_visibility_filter(
    db: Session, viewer: Optional[User], mine_only: bool
) -> Optional[ColumnElement[bool]]:
    """None means "no filter" -- platform admins see the whole catalogue either way."""
    if viewer is not None and viewer.role == "admin":
        return None
    if mine_only:
        # mine_only requires authentication; the route rejects an anonymous caller before here.
        return internal_activity_filter(db, viewer)  # type: ignore[arg-type]
    return public_activity_filter(viewer)


def program_visibility_filter(
    db: Session, viewer: Optional[User], mine_only: bool
) -> Optional[ColumnElement[bool]]:
    if viewer is not None and viewer.role == "admin":
        return None
    if mine_only:
        return internal_program_filter(db, viewer)  # type: ignore[arg-type]
    return public_program_filter(viewer)


def can_view_activity(db: Session, viewer: Optional[User], activity: Activity) -> bool:
    """Detail-endpoint check. Visible if it is publicly listed, if the caller's company owns or
    shares it, or if the caller has booked it."""
    if viewer is not None and viewer.role == "admin":
        return True
    conditions = [public_activity_filter(viewer)]
    if viewer is not None:
        conditions.append(internal_activity_filter(db, viewer))
    return (
        db.query(Activity.id)
        .filter(Activity.id == activity.id, or_(*conditions))
        .first()
        is not None
    )


def can_view_program(db: Session, viewer: Optional[User], program: Program) -> bool:
    if viewer is not None and viewer.role == "admin":
        return True
    conditions = [public_program_filter(viewer)]
    if viewer is not None:
        conditions.append(internal_program_filter(db, viewer))
    return (
        db.query(Program.id)
        .filter(Program.id == program.id, or_(*conditions))
        .first()
        is not None
    )
