# backend/scripts/seed_demo.py
"""
Seed the Outdaxius demo tenant set.

An empty database is the single most common reason a technical demo fails: every page renders an
empty state, and the prospect concludes the product does not work. This script produces a
database that looks like three real outdoor operators have been trading for three months.

Design rules, each of which exists because breaking it visibly damages a demo:

  * Deterministic. Fixed Faker/random seeds mean every run produces identical data, so a
    rehearsed demo script stays valid and a bug found on stage is reproducible.
  * Relative dates. Everything is generated as an offset from now(), never hardcoded. Stale dates
    in a live demo are the fastest possible credibility loss.
  * Idempotent. Re-running replaces the demo tenants rather than duplicating them.
  * Scoped. Deletes are confined to the seeded tenants and to users whose email ends in the demo
    suffix. There is no TRUNCATE anywhere in this file.
  * Guarded. Refuses to run unless APP_ENV is a non-production value, so it cannot be pointed at
    a customer database by accident.
  * Honest. Cancellations, fees and refunds are produced by calling the real
    app.services.cancellation code, not by writing plausible-looking numbers directly. If the
    policy changes, the demo data changes with it -- and if the policy is wrong, the demo shows
    it being wrong, which is the point.

Usage:
    python -m scripts.seed_demo              # seed (refuses if demo data already present)
    python -m scripts.seed_demo --reset      # remove existing demo data, then seed
    python -m scripts.seed_demo --purge      # remove existing demo data and stop
"""
from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from faker import Faker
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_credentials
from app.db.session import SessionLocal
from app.models.activity import Activity
from app.models.activity_schedule import ActivitySchedule
from app.models.assignment import Assignment
from app.models.booking import Booking
from app.models.company import Company
from app.models.company_payment_account import CompanyPaymentAccount
from app.models.companymember import CompanyMember
from app.models.invitation import InvitationCode
from app.models.location import Location
from app.models.membership_request import MembershipRequest
from app.models.payment import Payment
from app.models.program_schedule import ProgramSchedule
from app.models.programactivity import ProgramActivity
from app.models.programs import Program
from app.models.team import Team, TeamMember
from app.models.types import Types
from app.models.user import User
from app.services.cancellation import apply_cancellation, build_policy_snapshot
# app.core.security is the module the login endpoint verifies against (passlib CryptContext).
# Note app/utils/security.py also defines a hash_password, but it is unreachable: app/utils.py
# shadows the app/utils/ directory, which has no __init__.py. scripts/create_super_admin.py
# imports from there and is broken for the same reason -- see docs/DEMO_RUNBOOK.md.
from app.core.security import get_password_hash

from scripts import demo_data as D

# Every seeded human's email ends here. This is the scope predicate for teardown -- nothing
# outside this suffix is ever touched.
DEMO_EMAIL_SUFFIX = ".demo"

SEED = 20260806
CURRENCY = "CLP"

fake = Faker("es_CL")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _slug(raw: str) -> str:
    """ASCII-fold a Spanish name into an email local-part. The seeded roster is full of accents
    and ñ, and EmailStr in the response schemas rejects both."""
    out = raw.lower().strip().replace(" ", "")
    for ch, repl in (
        ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"),
        ("ü", "u"), ("ñ", "n"), ("'", ""), ("-", ""),
    ):
        out = out.replace(ch, repl)
    return out


# ------------------------------------------------------------------------------------------
# Safety
# ------------------------------------------------------------------------------------------
def assert_safe_environment() -> None:
    """Refuse to touch anything that looks like production. APP_ENV must be explicitly set to a
    known-safe value -- an unset APP_ENV is treated as unsafe rather than assumed to be dev."""
    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    allowed = {"demo", "dev", "development", "local", "test"}
    if app_env not in allowed:
        print(
            f"Refusing to run: APP_ENV is {app_env!r}, expected one of {sorted(allowed)}.\n"
            "This script writes and deletes data; it must never run against production.",
            file=sys.stderr,
        )
        raise SystemExit(2)


# ------------------------------------------------------------------------------------------
# Teardown
# ------------------------------------------------------------------------------------------
def purge_demo_data(db: Session) -> None:
    """Delete previously seeded demo data, children before parents.

    Scoped two ways: companies by the exact names in demo_data.COMPANIES, and users by the demo
    email suffix. Locations and types are shared reference data and are matched by their seeded
    values, so a hand-added row of either survives.
    """
    company_names = [c["name"] for c in D.COMPANIES]

    company_ids = [
        r[0] for r in db.query(Company.id).filter(Company.name.in_(company_names)).all()
    ]
    user_ids = [
        r[0] for r in db.query(User.id).filter(User.email.like(f"%{DEMO_EMAIL_SUFFIX}")).all()
    ]

    if not company_ids and not user_ids:
        return

    team_ids = [
        r[0] for r in db.query(Team.id).filter(Team.company_id.in_(company_ids)).all()
    ] if company_ids else []

    activity_ids = [
        r[0] for r in db.query(Activity.id).filter(Activity.created_by.in_(user_ids)).all()
    ] if user_ids else []
    program_ids = [
        r[0] for r in db.query(Program.id).filter(Program.created_by.in_(user_ids)).all()
    ] if user_ids else []

    program_schedule_ids = [
        r[0] for r in db.query(ProgramSchedule.id)
        .filter(ProgramSchedule.program_id.in_(program_ids)).all()
    ] if program_ids else []

    activity_schedule_ids = [
        r[0] for r in db.query(ActivitySchedule.id)
        .filter(ActivitySchedule.activity_id.in_(activity_ids)).all()
    ] if activity_ids else []

    booking_ids = []
    if activity_schedule_ids or program_schedule_ids:
        q = db.query(Booking.id).filter(
            Booking.activity_schedule_id.in_(activity_schedule_ids or [None])
            | Booking.program_schedule_id.in_(program_schedule_ids or [None])
        )
        booking_ids = [r[0] for r in q.all()]
    if user_ids:
        booking_ids += [
            r[0] for r in db.query(Booking.id).filter(Booking.user_id.in_(user_ids)).all()
        ]
    booking_ids = list(set(booking_ids))

    def bulk_delete(model, column, ids) -> int:
        if not ids:
            return 0
        return db.query(model).filter(column.in_(ids)).delete(synchronize_session=False)

    # Order matters: every child is removed before the row it points at.
    bulk_delete(Payment, Payment.booking_id, booking_ids)
    bulk_delete(Booking, Booking.id, booking_ids)
    bulk_delete(Assignment, Assignment.activity_schedule_id, activity_schedule_ids)
    bulk_delete(ActivitySchedule, ActivitySchedule.id, activity_schedule_ids)
    bulk_delete(ProgramSchedule, ProgramSchedule.id, program_schedule_ids)
    bulk_delete(ProgramActivity, ProgramActivity.program_id, program_ids)
    bulk_delete(ProgramActivity, ProgramActivity.activity_id, activity_ids)
    bulk_delete(Program, Program.id, program_ids)
    bulk_delete(Activity, Activity.id, activity_ids)
    bulk_delete(MembershipRequest, MembershipRequest.company_id, company_ids)
    bulk_delete(InvitationCode, InvitationCode.company_id, company_ids)
    bulk_delete(TeamMember, TeamMember.team_id, team_ids)
    bulk_delete(Team, Team.id, team_ids)
    bulk_delete(CompanyMember, CompanyMember.companyid, company_ids)
    bulk_delete(CompanyPaymentAccount, CompanyPaymentAccount.company_id, company_ids)
    bulk_delete(Company, Company.id, company_ids)
    bulk_delete(User, User.id, user_ids)

    db.commit()
    print(
        f"Purged demo data: {len(company_ids)} companies, {len(user_ids)} users, "
        f"{len(booking_ids)} bookings."
    )


def demo_data_present(db: Session) -> bool:
    names = [c["name"] for c in D.COMPANIES]
    return db.query(Company.id).filter(Company.name.in_(names)).first() is not None


# ------------------------------------------------------------------------------------------
# Reference data
# ------------------------------------------------------------------------------------------
def seed_types(db: Session) -> dict[str, Types]:
    """Types are global reference data, shared across tenants. Reused if already present so a
    re-seed never orphans activities belonging to non-demo companies."""
    out: dict[str, Types] = {}
    for type_name, experience_type in D.TYPES:
        row = db.query(Types).filter(Types.type_name == type_name).first()
        if not row:
            row = Types(type_name=type_name, experience_type=experience_type)
            db.add(row)
            db.flush()
        out[type_name] = row
    return out


def seed_locations(db: Session) -> list[Location]:
    out: list[Location] = []
    for display_name, lat, lon in D.LOCATIONS:
        row = db.query(Location).filter(Location.display_name == display_name).first()
        if not row:
            row = Location(display_name=display_name, lat=lat, lon=lon, source="manual")
            db.add(row)
            db.flush()
        out.append(row)
    return out


# ------------------------------------------------------------------------------------------
# People and tenants
# ------------------------------------------------------------------------------------------
def seed_users_and_companies(db: Session, password_hash: str) -> dict:
    """Create the four named logins, the supporting guide roster, and the three tenants with
    their teams, memberships and demo payment accounts."""
    ctx: dict = {"users": {}, "companies": {}, "teams": {}, "guides": {}}

    # Owners first -- Company.createdby is NOT NULL, so a creator must exist before its company.
    for login in D.DEMO_LOGINS:
        user = User(
            email=login["email"],
            password_hash=password_hash,
            display_name=login["display_name"],
            first_name=login["first_name"],
            last_name=login["last_name"],
            role=login["role"],
            is_active=True,
            phone=f"+56 9 {random.randint(4000, 9999)} {random.randint(1000, 9999)}",
            preferred_language="es",
        )
        db.add(user)
        db.flush()
        ctx["users"][login["key"]] = user

    owner = ctx["users"]["owner"]

    for spec in D.COMPANIES:
        company = Company(
            name=spec["name"],
            legal_name=spec["legal_name"],
            trade_name=spec["trade_name"],
            description=spec["description"],
            createdby=owner.id,
            license_tier=spec["tier"],
            is_active=True,
            country=spec["country"],
            currency=spec["currency"],
            address=spec["address"],
            entity_type=spec["entity_type"],
            incorporation_date=datetime.strptime(spec["incorporation_date"], "%Y-%m-%d").date(),
            legal_representive=spec["legal_representive"],
            legal_representive_text=spec["legal_representive_text"],
            legal_representive_phone=spec["legal_representive_phone"],
            is_multinational=False,
            # Well clear of the demo horizon, so nothing expires mid-quarter and silently
            # disables a tenant during a call.
            subscription_expires_at=now_utc() + timedelta(days=365),
        )
        db.add(company)
        db.flush()
        ctx["companies"][spec["key"]] = company

        team = Team(
            name=spec["team_name"],
            description=f"Operational team for {spec['name']}.",
            created_by=owner.id,
            company_id=company.id,
            is_active=True,
        )
        db.add(team)
        db.flush()
        ctx["teams"][spec["key"]] = team

        # Every company is its own merchant of record. The demo provider stands in for a real
        # gateway: same Payment rows, same booking transitions, no external account and no real
        # money. credentials_encrypted is NOT NULL, so even the demo account stores (encrypted)
        # placeholder credentials rather than a sentinel value.
        db.add(
            CompanyPaymentAccount(
                company_id=company.id,
                provider="demo",
                external_account_id=f"demo-acct-{spec['key']}",
                credentials_encrypted=encrypt_credentials(
                    {"note": "demo provider — no real credentials", "company": spec["key"]}
                ),
                charges_enabled=True,
                currency=CURRENCY,
                is_sandbox=True,
                verified_at=now_utc() - timedelta(days=120),
            )
        )

    # Named logins into their company/team
    for login in D.DEMO_LOGINS:
        if not login["company"]:
            continue
        user = ctx["users"][login["key"]]
        company = ctx["companies"][login["company"]]
        team = ctx["teams"][login["company"]]
        db.add(
            CompanyMember(
                companyid=company.id,
                userid=user.id,
                position=login["position"],
                is_admin=login["is_admin"],
                is_active=True,
                joinedat=(now_utc() - timedelta(days=400)).date(),
            )
        )
        db.add(TeamMember(team_id=team.id, user_id=user.id, role_level=login["role_level"]))

    # Supporting guide roster
    for company_key, roster in D.GUIDES.items():
        company = ctx["companies"][company_key]
        team = ctx["teams"][company_key]
        ctx["guides"][company_key] = []
        for idx, (first, last, role_level, position) in enumerate(roster):
            local = _slug(f"{first}.{last}")
            email = f"{local}@{company_key}{DEMO_EMAIL_SUFFIX}"
            user = User(
                email=email,
                password_hash=password_hash,
                display_name=f"{first} {last}",
                first_name=first,
                last_name=last,
                role="guide",
                is_active=True,
                phone=f"+56 9 {random.randint(4000, 9999)} {random.randint(1000, 9999)}",
                preferred_language="es",
            )
            db.add(user)
            db.flush()
            db.add(
                CompanyMember(
                    companyid=company.id,
                    userid=user.id,
                    position=position,
                    is_admin=(role_level <= 2),
                    is_active=True,
                    joinedat=(now_utc() - timedelta(days=random.randint(60, 900))).date(),
                )
            )
            db.add(TeamMember(team_id=team.id, user_id=user.id, role_level=role_level))
            ctx["guides"][company_key].append(user)

    # The named guide login has to be in the staffing pool, not just a team member. Without this
    # she is never picked by seed_assignments and "My Assignments" -- the entire point of the
    # guide login -- renders with a single row.
    for login in D.DEMO_LOGINS:
        if login["company"] and login["role"] == "guide" and login["role_level"] == 4:
            ctx["guides"][login["company"]].append(ctx["users"][login["key"]])

    # Each tenant's most senior named login, used as the author of that tenant's catalogue.
    # app.services.company_usage attributes activities and programs through created_by, so the
    # creator must be a member of the company whose plan limits are meant to count them.
    ctx["owners"] = {}
    for login in D.DEMO_LOGINS:
        if not login["company"]:
            continue
        key = login["company"]
        current = ctx["owners"].get(key)
        if current is None or login["role_level"] < current[1]:
            ctx["owners"][key] = (ctx["users"][login["key"]], login["role_level"])
    ctx["owners"] = {k: v[0] for k, v in ctx["owners"].items()}

    db.flush()
    return ctx


def seed_customers(db: Session, password_hash: str, count: int) -> list[User]:
    """The booking population. Faker is appropriate here and only here -- these names exist to
    give bookings a plausible spread of humans, and nobody reads them closely."""
    customers: list[User] = []
    seen: set[str] = set()
    for _ in range(count):
        first = fake.first_name()
        last = fake.last_name()
        base = _slug(f"{first}.{last}")
        email = f"{base}@viajeros{DEMO_EMAIL_SUFFIX}"
        n = 2
        while email in seen:
            email = f"{base}{n}@viajeros{DEMO_EMAIL_SUFFIX}"
            n += 1
        seen.add(email)

        user = User(
            email=email,
            password_hash=password_hash,
            display_name=f"{first} {last}",
            first_name=first,
            last_name=last,
            role="client",
            is_active=True,
            phone=f"+56 9 {random.randint(4000, 9999)} {random.randint(1000, 9999)}",
            preferred_language="es",
        )
        db.add(user)
        customers.append(user)
    db.flush()
    return customers


# ------------------------------------------------------------------------------------------
# Catalogue
# ------------------------------------------------------------------------------------------
def seed_catalogue(db: Session, ctx: dict, types: dict, locations: list[Location]) -> dict:
    """Activities and programs, created by each tenant's own senior staff so the historical usage
    queries in app.services.company_usage (which join through company_members.userid) attribute
    them to the right company."""
    catalogue: dict = {"activities": {}, "programs": {}}

    for company_key, specs in D.ACTIVITIES.items():
        team = ctx["teams"][company_key]
        staff = ctx["guides"][company_key]
        creator = ctx["owners"].get(company_key) or staff[0]
        catalogue["activities"][company_key] = []

        for title, type_name, loc_idx, price, min_p, max_p, description in specs:
            leader = random.choice(staff)
            activity = Activity(
                title=title,
                description=description,
                activity_type=types[type_name].id,
                created_by=creator.id,
                location_id=locations[loc_idx].id,
                guide_leader=leader.id,
                team_id=team.id,
                is_shared=False,
                gallery=[],
            )
            db.add(activity)
            db.flush()
            catalogue["activities"][company_key].append((activity, Decimal(price), min_p, max_p))

    for company_key, specs in D.PROGRAMS.items():
        team = ctx["teams"][company_key]
        staff = ctx["guides"][company_key]
        creator = ctx["owners"].get(company_key) or staff[0]
        catalogue["programs"][company_key] = []

        for title, type_name, activity_idxs, price, min_p, max_p, description in specs:
            program = Program(
                title=title,
                description=description,
                program_type=types[type_name].id,
                created_by=creator.id,
                guide_leader=random.choice(staff).id,
                team_id=team.id,
                is_shared=False,
                gallery=[],
                min_activities=max(2, len(activity_idxs)),
            )
            db.add(program)
            db.flush()
            for a_idx in activity_idxs:
                activity, *_ = catalogue["activities"][company_key][a_idx]
                db.add(ProgramActivity(program_id=program.id, activity_id=activity.id))
            catalogue["programs"][company_key].append((program, Decimal(price), min_p, max_p))

    db.flush()
    return catalogue


def seed_schedules(db: Session, ctx: dict, catalogue: dict) -> dict:
    """Roughly 90 days of departures: history behind us so reports have something to aggregate,
    and departures ahead so dashboards have work to show today.

    Patagonia is deliberately parked just under the basic tier's 50-schedule cap (see
    app.services.plan_limits) so an owner can try to add one more departure on a live call and
    watch the upgrade path fire. Schedules are the right limit to demo against: they carry no
    hand-written content, so pushing the count to 48 needs no invented activity names.
    """
    schedules: dict = {"activity": {}, "program": {}}
    now = now_utc()

    # (past_departures, upcoming_departures) per activity, chosen per tenant so Patagonia lands
    # just under its cap while Andes looks like a busy operator.
    # Patagonia: 4 activities x (6 past + 4 upcoming) = 40 activity schedules, plus 2 programs
    # x 4 = 8 program schedules = 48 total, against the basic tier's cap of 50. Two departures of
    # headroom is the sweet spot -- enough that the tenant looks like a going concern, few enough
    # that the owner hits the wall on the second click.
    cadence = {
        "andes": (5, 4),
        "patagonia": (6, 4),
        "cordillera": (4, 3),
    }

    for company_key, entries in catalogue["activities"].items():
        company = ctx["companies"][company_key]
        past_n, upcoming_n = cadence[company_key]
        schedules["activity"][company_key] = []

        for activity, price, min_p, max_p in entries:
            for i in range(past_n):
                start = now - timedelta(days=random.randint(4, 88), hours=random.randint(0, 6))
                start = start.replace(hour=random.choice([6, 7, 8, 9]), minute=0, second=0, microsecond=0)
                end = start + timedelta(hours=random.choice([6, 8, 10, 24, 48]))
                sched = ActivitySchedule(
                    activity_id=activity.id,
                    start_time=start,
                    end_time=end,
                    price=price,
                    status="confirmed",
                    min_participants=min_p,
                    max_participants=max_p,
                    selling_company_id=company.id,
                )
                db.add(sched)
                db.flush()
                schedules["activity"][company_key].append((sched, price, max_p, True))

            for i in range(upcoming_n):
                start = now + timedelta(days=random.randint(2, 75))
                start = start.replace(hour=random.choice([6, 7, 8, 9]), minute=0, second=0, microsecond=0)
                end = start + timedelta(hours=random.choice([6, 8, 10, 24, 48]))
                sched = ActivitySchedule(
                    activity_id=activity.id,
                    start_time=start,
                    end_time=end,
                    price=price,
                    status=random.choice(["confirmed", "confirmed", "pending"]),
                    min_participants=min_p,
                    max_participants=max_p,
                    selling_company_id=company.id,
                )
                db.add(sched)
                db.flush()
                schedules["activity"][company_key].append((sched, price, max_p, False))

    for company_key, entries in catalogue["programs"].items():
        company = ctx["companies"][company_key]
        schedules["program"][company_key] = []

        for program, price, min_p, max_p in entries:
            for is_past in (True, True, False, False):
                if is_past:
                    start = now - timedelta(days=random.randint(10, 85))
                else:
                    start = now + timedelta(days=random.randint(5, 80))
                start = start.replace(hour=8, minute=0, second=0, microsecond=0)
                end = start + timedelta(days=random.randint(2, 8))
                sched = ProgramSchedule(
                    program_id=program.id,
                    start_time=start,
                    end_time=end,
                    price=price,
                    status="confirmed" if is_past else random.choice(["confirmed", "confirmed", "pending"]),
                    min_participants=min_p,
                    max_participants=max_p,
                    selling_company_id=company.id,
                )
                db.add(sched)
                db.flush()
                schedules["program"][company_key].append((sched, price, max_p, is_past))

    db.flush()
    return schedules


# ------------------------------------------------------------------------------------------
# Bookings, payments, cancellations
# ------------------------------------------------------------------------------------------
def _participants(count: int) -> list[dict]:
    out = []
    for _ in range(count):
        out.append(
            {
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                # app.schemas.booking.Participant restricts this to national_id | passport.
                # "rut" is what a Chilean operator would say, but it is not a value the API
                # accepts, and seeding it makes GET /bookings fail response validation entirely.
                "id_type": "national_id",
                "id_number": f"{random.randint(9, 24)}.{random.randint(100, 999)}.{random.randint(100, 999)}-{random.choice('0123456789K')}",
                "birth_date": fake.date_of_birth(minimum_age=18, maximum_age=68).isoformat(),
            }
        )
    return out


def _weighted_status(weights: list[tuple[str, int]]) -> tuple[str, int]:
    total = sum(w for _, w in weights)
    roll = random.randint(1, total)
    upto = 0
    for idx, (status, weight) in enumerate(weights):
        upto += weight
        if roll <= upto:
            return status, idx
    return weights[-1][0], len(weights) - 1


def seed_bookings(db: Session, ctx: dict, schedules: dict, customers: list[User]) -> dict:
    """Bookings across every terminal state, with payments and -- where cancelled -- fees and
    refunds computed by the real cancellation service rather than written by hand.

    The named customer login (client@outdaxius.demo) is given its own bookings in several states
    so that logging in as the customer shows a populated trip history rather than an empty one.
    """
    stats = {"bookings": 0, "payments": 0, "cancelled": 0, "refunded": 0, "fees": Decimal("0")}
    now = now_utc()
    client_user = ctx["users"]["client"]

    all_schedules: list[tuple[object, Decimal, int, bool, str]] = []
    for company_key, rows in schedules["activity"].items():
        for sched, price, max_p, is_past in rows:
            all_schedules.append((sched, price, max_p, is_past, "activity"))
    for company_key, rows in schedules["program"].items():
        for sched, price, max_p, is_past in rows:
            all_schedules.append((sched, price, max_p, is_past, "program"))

    for sched, price, max_p, is_past, kind in all_schedules:
        # Fill rate varies per departure so the capacity chart in Phase 4 has a real distribution
        # rather than every trip sitting at the same occupancy.
        fill = random.choice([0.2, 0.35, 0.5, 0.6, 0.75, 0.8, 0.9, 1.0])
        seats_target = max(1, int(max_p * fill))
        seats_booked = 0
        attempts = 0
        # uq_booking_user_activity / uq_booking_user_program: a user may hold at most one booking
        # per departure. That is a real business rule, so the seeder respects it rather than
        # working around it -- one customer books a party, they do not book twice.
        booked_here: set[UUID] = set()

        while seats_booked < seats_target and attempts < 30:
            attempts += 1
            party = random.choice([1, 1, 2, 2, 2, 3, 4])
            if seats_booked + party > max_p:
                party = max_p - seats_booked
            if party <= 0:
                break

            available = [c for c in customers if c.id not in booked_here]
            if not available:
                break
            customer = random.choice(available)
            booked_here.add(customer.id)
            weights = D.PAST_STATUS_WEIGHTS if is_past else D.UPCOMING_STATUS_WEIGHTS
            status, variant = _weighted_status(weights)

            amount = (price * Decimal(party)).quantize(Decimal("0.01"))
            created_at = sched.start_time - timedelta(days=random.randint(3, 45))

            booking = Booking(
                user_id=customer.id,
                activity_schedule_id=sched.id if kind == "activity" else None,
                program_schedule_id=sched.id if kind == "program" else None,
                status="confirmed" if status == "cancelled" else status,
                participants_count=party,
                participants=_participants(party),
                attendance_status="not_attended",
                policy_snapshot=build_policy_snapshot(),
                created_at=created_at,
            )
            db.add(booking)
            db.flush()
            stats["bookings"] += 1
            seats_booked += party

            paid = status in ("confirmed", "cancelled")
            payment: Optional[Payment] = None
            if paid:
                payment = Payment(
                    booking_id=booking.id,
                    amount=amount,
                    currency=CURRENCY,
                    status="succeeded",
                    provider="demo",
                    provider_ref=f"demo-{booking.id}",
                    reference=f"DEMO-{str(booking.id)[:8].upper()}",
                    created_at=created_at,
                )
                db.add(payment)
                db.flush()
                stats["payments"] += 1

            if status == "cancelled":
                # Vendor cancellations are the 4th weighted variant for past departures and drive
                # the published cancellation-rate badge (app.services.vendor_reputation), which
                # counts cancelled_by_party == "vendor" only.
                is_vendor = is_past and variant == 3
                party_who = "vendor" if is_vendor else "client"
                actor = ctx["users"]["owner"] if is_vendor else customer
                schedule_start = sched.start_time

                # Cancel at a believable moment in the run-up, so the hour-tiered fee schedule
                # actually produces a spread of outcomes instead of all-or-nothing.
                cancel_at = schedule_start - timedelta(hours=random.choice([4, 12, 30, 72, 120, 200, 400]))
                if cancel_at < created_at:
                    cancel_at = created_at + timedelta(hours=6)

                hours_before = (schedule_start - cancel_at).total_seconds() / 3600
                refund = apply_cancellation(
                    booking=booking,
                    cancelled_by=actor,
                    cancelled_by_party=party_who,
                    reason=(
                        "Weather — unsafe conditions forecast"
                        if is_vendor
                        else random.choice(
                            [
                                "Change of travel plans",
                                "Illness",
                                "Group could not make the date",
                                "Found a different date",
                            ]
                        )
                    ),
                    amount_paid=amount,
                    schedule_start=schedule_start,
                )
                # apply_cancellation stamps cancelled_at with now(); the demo needs it stamped at
                # the moment the fee tier was actually computed from, or the booking would show a
                # fee inconsistent with its own timestamp.
                booking.cancelled_at = cancel_at

                stats["cancelled"] += 1
                stats["fees"] += booking.cancellation_fee or Decimal("0")

                if payment is not None and refund > 0:
                    booking.refund_status = "succeeded"
                    booking.refund_reference = f"demo-refund-{str(booking.id)[:8]}"
                    payment.status = "refunded" if refund >= amount else "partially_refunded"
                    stats["refunded"] += 1
                elif payment is not None:
                    # Fee consumed the whole payment: nothing to move, and the policy says so.
                    booking.refund_status = "not_required"

            elif is_past and status == "confirmed":
                booking.attendance_status = "no_show" if variant == 2 else "attended"

        # Give the named customer login a stake in a handful of departures, so their trip history
        # is populated in every state the UI can render.
        if random.random() < 0.12 and client_user.id not in booked_here:
            party = random.choice([1, 2])
            amount = (price * Decimal(party)).quantize(Decimal("0.01"))
            created_at = sched.start_time - timedelta(days=random.randint(5, 30))
            booking = Booking(
                user_id=client_user.id,
                activity_schedule_id=sched.id if kind == "activity" else None,
                program_schedule_id=sched.id if kind == "program" else None,
                status="confirmed" if is_past else random.choice(["confirmed", "pending"]),
                participants_count=party,
                participants=_participants(party),
                attendance_status="attended" if is_past else "not_attended",
                policy_snapshot=build_policy_snapshot(),
                created_at=created_at,
            )
            db.add(booking)
            db.flush()
            stats["bookings"] += 1
            if booking.status == "confirmed":
                db.add(
                    Payment(
                        booking_id=booking.id,
                        amount=amount,
                        currency=CURRENCY,
                        status="succeeded",
                        provider="demo",
                        provider_ref=f"demo-{booking.id}",
                        reference=f"DEMO-{str(booking.id)[:8].upper()}",
                        created_at=created_at,
                    )
                )
                stats["payments"] += 1

    db.flush()
    return stats


# ------------------------------------------------------------------------------------------
# Staffing
# ------------------------------------------------------------------------------------------
def seed_assignments(db: Session, ctx: dict, schedules: dict) -> dict:
    """Staff the departures, and deliberately leave one live conflict for the demo.

    The conflict: Javiera Rojas (the guide login) holds an ACCEPTED assignment on one upcoming
    departure, while a second, time-overlapping departure is left unstaffed. Trying to assign her
    to that second one on a call makes app.services.assignments.check_schedule_conflict fire in
    front of the prospect, which demonstrates the feature far better than describing it.
    """
    stats = {"assignments": 0, "conflict_pair": None}
    now = now_utc()

    for company_key, rows in schedules["activity"].items():
        company = ctx["companies"][company_key]
        team = ctx["teams"][company_key]
        staff = ctx["guides"][company_key]
        proposer = ctx["users"]["owner"]

        for sched, price, max_p, is_past in rows:
            # Not every upcoming departure is staffed -- an operator with a fully staffed calendar
            # has nothing for the owner to do on the dashboard.
            if not is_past and random.random() < 0.25:
                continue

            crew_size = 1 if max_p <= 8 else 2
            crew = random.sample(staff, min(crew_size, len(staff)))
            for idx, guide in enumerate(crew):
                if _has_overlap(db, guide.id, sched):
                    continue
                status = "accepted" if is_past or random.random() < 0.75 else "proposed"
                db.add(
                    Assignment(
                        activity_schedule_id=sched.id,
                        user_id=guide.id,
                        home_team_id=team.id,
                        home_company_id=company.id,
                        is_leader=(idx == 0),
                        status=status,
                        proposed_by=proposer.id,
                        proposed_at=sched.start_time - timedelta(days=random.randint(5, 30)),
                        responded_at=(
                            sched.start_time - timedelta(days=random.randint(1, 4))
                            if status == "accepted"
                            else None
                        ),
                    )
                )
                db.flush()
                stats["assignments"] += 1

    # Build the planted conflict last, so nothing above can accidentally satisfy or block it.
    javiera = ctx["users"]["guide"]
    andes_team = ctx["teams"]["andes"]
    andes_company = ctx["companies"]["andes"]
    upcoming = sorted(
        [s for s in schedules["activity"]["andes"] if not s[3]],
        key=lambda r: r[0].start_time,
    )

    anchor = None
    overlapping = None
    for sched, *_ in upcoming:
        if anchor is None:
            anchor = sched
            continue
        if sched.start_time < anchor.end_time and sched.end_time > anchor.start_time:
            overlapping = sched
            break

    if anchor is not None and overlapping is None:
        # No natural overlap in the generated calendar -- move a later departure onto the anchor's
        # window so the scenario is guaranteed to exist rather than left to chance.
        for sched, *_ in upcoming:
            if sched.id == anchor.id:
                continue
            sched.start_time = anchor.start_time + timedelta(hours=1)
            sched.end_time = anchor.end_time + timedelta(hours=1)
            overlapping = sched
            break

    if anchor is not None and overlapping is not None:
        # Clear the anchor completely before restaffing it. uq_assignment_single_leader permits
        # only one leader per departure among proposed/accepted rows, so removing just Javiera's
        # own row would leave whichever guide the general loop made leader still holding the slot.
        db.query(Assignment).filter(
            Assignment.activity_schedule_id == anchor.id
        ).delete(synchronize_session=False)

        db.add(
            Assignment(
                activity_schedule_id=anchor.id,
                user_id=javiera.id,
                home_team_id=andes_team.id,
                home_company_id=andes_company.id,
                is_leader=True,
                status="accepted",
                proposed_by=ctx["users"]["owner"].id,
                proposed_at=now - timedelta(days=6),
                responded_at=now - timedelta(days=5),
            )
        )
        # The overlapping departure is left with no assignment for Javiera on purpose.
        db.query(Assignment).filter(
            Assignment.activity_schedule_id == overlapping.id
        ).delete(synchronize_session=False)

        stats["assignments"] += 1
        stats["conflict_pair"] = (str(anchor.id), str(overlapping.id))

    db.flush()
    return stats


def _has_overlap(db: Session, user_id: UUID, schedule) -> bool:
    """Mirror of app.services.assignments.check_schedule_conflict, used while seeding so the
    generated roster does not contain accidental double-bookings. The one conflict in the demo
    should be the planted one, not noise."""
    return (
        db.query(Assignment.id)
        .join(ActivitySchedule, ActivitySchedule.id == Assignment.activity_schedule_id)
        .filter(
            Assignment.user_id == user_id,
            Assignment.status == "accepted",
            ActivitySchedule.start_time < schedule.end_time,
            ActivitySchedule.end_time > schedule.start_time,
        )
        .first()
        is not None
    )


# ------------------------------------------------------------------------------------------
# Inbox: pending requests and open invitations
# ------------------------------------------------------------------------------------------
def seed_inbox(db: Session, ctx: dict, customers: list[User]) -> dict:
    """An admin screen with an empty inbox demos as a dead screen. These give the owner login
    something waiting for a decision."""
    stats = {"requests": 0, "invitations": 0}
    andes = ctx["companies"]["andes"]
    andes_team = ctx["teams"]["andes"]
    owner = ctx["users"]["owner"]
    now = now_utc()

    applicants = random.sample(customers, 4)
    for applicant in applicants:
        db.add(
            MembershipRequest(
                direction="application",
                team_id=andes_team.id,
                company_id=andes.id,
                target_user_id=applicant.id,
                target_email=applicant.email,
                offered_level=4,
                created_by=applicant.id,
                target_consent="granted",
            )
        )
        stats["requests"] += 1

    for i, email in enumerate(
        ["nueva.guia@andes.demo", "instructor.invitado@andes.demo"]
    ):
        db.add(
            InvitationCode(
                code=f"ANDES-{2026 + i}-{random.randint(1000, 9999)}",
                company_id=andes.id,
                created_by=owner.id,
                invited_email=email,
                status="pending",
                used=False,
                expires_at=now + timedelta(days=random.randint(5, 21)),
            )
        )
        stats["invitations"] += 1

    db.flush()
    return stats


# ------------------------------------------------------------------------------------------
# Reporting
# ------------------------------------------------------------------------------------------
def print_summary(db: Session, ctx: dict, stats: dict) -> None:
    print("\n" + "=" * 78)
    print("OUTDAXIUS DEMO DATA SEEDED")
    print("=" * 78)

    print("\nTenants")
    for spec in D.COMPANIES:
        company = ctx["companies"][spec["key"]]
        activities = db.execute(
            text(
                "SELECT COUNT(*) FROM activities a JOIN company_members cm "
                "ON a.created_by = cm.userid WHERE cm.companyid = :cid"
            ),
            {"cid": str(company.id)},
        ).scalar()
        scheds = db.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*) FROM activity_schedules WHERE selling_company_id = :cid)
                + (SELECT COUNT(*) FROM program_schedules  WHERE selling_company_id = :cid)
                """
            ),
            {"cid": str(company.id)},
        ).scalar()
        print(
            f"  {spec['name']:<26} tier={spec['tier']:<11} activities={activities:<4} schedules={scheds}"
        )

    print("\nBookings")
    print(f"  total          {stats['bookings']['bookings']}")
    print(f"  payments       {stats['bookings']['payments']}")
    print(f"  cancelled      {stats['bookings']['cancelled']}")
    print(f"  refunded       {stats['bookings']['refunded']}")
    print(f"  fees retained  {stats['bookings']['fees']} {CURRENCY}")
    print(f"\nAssignments      {stats['assignments']['assignments']}")
    if stats["assignments"]["conflict_pair"]:
        anchor, overlapping = stats["assignments"]["conflict_pair"]
        print("  Planted conflict for the demo:")
        print(f"    Javiera Rojas is ACCEPTED on activity_schedule {anchor}")
        print(f"    Overlapping, unstaffed departure:      {overlapping}")
        print("    Assigning her to the second one will trip the conflict check on stage.")

    print(f"\nInbox            {stats['inbox']['requests']} membership requests, "
          f"{stats['inbox']['invitations']} open invitations")

    print("\n" + "-" * 78)
    print("DEMO LOGINS   (password for every account below: " + D.DEMO_PASSWORD + ")")
    print("-" * 78)
    for login in D.DEMO_LOGINS:
        print(f"  {login['email']:<28} {login['blurb']}")
    print("-" * 78 + "\n")


# ------------------------------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the Outdaxius demo dataset.")
    parser.add_argument("--reset", action="store_true", help="Purge existing demo data, then seed.")
    parser.add_argument("--purge", action="store_true", help="Purge existing demo data and exit.")
    parser.add_argument("--customers", type=int, default=90, help="Number of demo customers.")
    args = parser.parse_args()

    assert_safe_environment()

    random.seed(SEED)
    Faker.seed(SEED)

    db = SessionLocal()
    try:
        if args.purge:
            purge_demo_data(db)
            return 0

        if demo_data_present(db):
            if not args.reset:
                print(
                    "Demo data already present. Re-run with --reset to replace it, "
                    "or --purge to remove it.",
                    file=sys.stderr,
                )
                return 1
            purge_demo_data(db)

        # One Argon2 hash, reused for every seeded account. Argon2 is deliberately slow
        # (~50ms/hash by design); hashing the same demo password 120 times would add minutes to
        # every run for no benefit whatsoever.
        password_hash = get_password_hash(D.DEMO_PASSWORD)

        types = seed_types(db)
        locations = seed_locations(db)
        ctx = seed_users_and_companies(db, password_hash)
        customers = seed_customers(db, password_hash, args.customers)
        catalogue = seed_catalogue(db, ctx, types, locations)
        schedules = seed_schedules(db, ctx, catalogue)

        stats = {
            "bookings": seed_bookings(db, ctx, schedules, customers),
            "assignments": seed_assignments(db, ctx, schedules),
            "inbox": seed_inbox(db, ctx, customers),
        }

        db.commit()
        print_summary(db, ctx, stats)
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
