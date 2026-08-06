# backend/scripts/verify_demo.py
"""
Assert that the seeded demo database is actually demo-ready.

Run this after every seed, and especially after the nightly reset -- a seeder that silently
half-succeeds produces exactly the empty screen the demo exists to avoid, and the first person to
notice should not be the prospect.

Every check is phrased as something a viewer would see on a call, not as an internal invariant.
Where possible the check calls the same service the application calls, so a passing run means the
feature works, not merely that rows exist.

Usage:
    python -m scripts.verify_demo          # exits non-zero if any check fails
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.core.security import verify_password
from app.db.session import SessionLocal
from app.models.activity import Activity
from app.models.activity_schedule import ActivitySchedule
from app.models.assignment import Assignment
from app.models.booking import Booking
from app.models.company import Company
from app.models.invitation import InvitationCode
from app.models.membership_request import MembershipRequest
from app.models.payment import Payment
from app.models.programs import Program
from app.models.user import User
from app.services.assignments import check_schedule_conflict
from app.services.company_usage import historical_usage
from app.services.payment_accounts import get_any_charges_enabled_account
from app.services.plan_limits import get_limits_for_tier
from app.services.vendor_reputation import get_vendor_cancellation_rate

from scripts import demo_data as D

_failures: list[str] = []


def check(label: str, passed: bool, detail: str = "") -> None:
    mark = "PASS" if passed else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{mark}] {label}{suffix}")
    if not passed:
        _failures.append(label)


def section(title: str) -> None:
    print(f"\n{title}")


def main() -> int:
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    try:
        section("Demo logins authenticate")
        for login in D.DEMO_LOGINS:
            user = db.query(User).filter(User.email == login["email"]).first()
            check(
                login["email"],
                user is not None and verify_password(D.DEMO_PASSWORD, user.password_hash),
            )

        section("Tenants exist with a catalogue")
        for spec in D.COMPANIES:
            company = db.query(Company).filter(Company.name == spec["name"]).first()
            if company is None:
                check(spec["name"], False, "company missing")
                continue
            usage = historical_usage(db, company.id)
            check(
                spec["name"],
                usage["activities"] > 0 and usage["schedules_total"] > 0,
                f"{usage['activities']} activities, {usage['schedules_total']} schedules, "
                f"tier {company.license_tier}",
            )

        section("No named login lands on an empty screen")
        by_email = {u.email: u for u in db.query(User).all()}
        client = by_email.get("client@outdaxius.demo")
        guide = by_email.get("guide@andes.demo")
        owner = by_email.get("owner@andes.demo")

        client_bookings = (
            db.query(Booking).filter(Booking.user_id == client.id).count() if client else 0
        )
        check("customer has trip history", client_bookings >= 5, f"{client_bookings} bookings")

        guide_assignments = (
            db.query(Assignment).filter(Assignment.user_id == guide.id).count() if guide else 0
        )
        check("guide has assignments", guide_assignments >= 3, f"{guide_assignments} assignments")

        andes = db.query(Company).filter(Company.name == "Andes Expeditions").first()
        if andes:
            reqs = (
                db.query(MembershipRequest)
                .filter(MembershipRequest.company_id == andes.id)
                .count()
            )
            invs = db.query(InvitationCode).filter(InvitationCode.company_id == andes.id).count()
            check("owner has an inbox", reqs > 0 and invs > 0, f"{reqs} requests, {invs} invites")

        section("Money is coherent")
        total = db.query(Booking).count()
        cancelled = db.query(Booking).filter(Booking.status == "cancelled").count()
        pct = (cancelled * 100 // total) if total else 0
        check("cancellation rate is plausible", 5 <= pct <= 25, f"{cancelled}/{total} = {pct}%")

        missing_fee = (
            db.query(Booking)
            .filter(Booking.status == "cancelled", Booking.cancellation_fee.is_(None))
            .count()
        )
        check("every cancellation carries a computed fee", missing_fee == 0, f"{missing_fee} missing")

        negative = db.query(Booking).filter(Booking.refund_amount < 0).count()
        check("no negative refunds", negative == 0)

        mismatched = 0
        for booking in db.query(Booking).filter(Booking.status == "cancelled").all():
            payment = db.query(Payment).filter(Payment.booking_id == booking.id).first()
            if payment is None or booking.cancellation_fee is None or booking.refund_amount is None:
                continue
            if booking.cancellation_fee + booking.refund_amount != payment.amount:
                mismatched += 1
        check("fee + refund equals amount paid", mismatched == 0, f"{mismatched} mismatched")

        section("Features have something to show")
        if andes:
            rate = get_vendor_cancellation_rate(db, andes.id)
            check(
                "hero tenant publishes a cancellation rate",
                rate["cancellation_rate"] is not None,
                f"{rate['cancellation_rate']} over {rate['total_bookings']} bookings",
            )

        conflict = None
        if guide:
            accepted = (
                db.query(Assignment)
                .filter(Assignment.user_id == guide.id, Assignment.status == "accepted")
                .all()
            )
            for assignment in accepted:
                anchor = db.get(ActivitySchedule, assignment.activity_schedule_id)
                if anchor is None:
                    continue
                candidates = (
                    db.query(ActivitySchedule)
                    .filter(
                        ActivitySchedule.id != anchor.id,
                        ActivitySchedule.start_time < anchor.end_time,
                        ActivitySchedule.end_time > anchor.start_time,
                    )
                    .all()
                )
                for candidate in candidates:
                    if check_schedule_conflict(db, guide.id, candidate):
                        conflict = (anchor.id, candidate.id)
                        break
                if conflict:
                    break
        check(
            "a live assignment conflict is available to demo",
            conflict is not None,
            f"assign the guide to schedule {conflict[1]}" if conflict else "none found",
        )

        basic = db.query(Company).filter(Company.license_tier == "basic").first()
        if basic:
            usage = historical_usage(db, basic.id)
            limits = get_limits_for_tier(basic.license_tier)
            cap = limits.max_schedules_total
            used = usage["schedules_total"]
            check(
                "freemium tenant is just under its cap",
                cap is not None and used < cap and (cap - used) <= 5,
                f"{basic.name}: {used}/{cap} schedules",
            )

        section("Payment rail is wired")
        for company in db.query(Company).all():
            account = get_any_charges_enabled_account(db, company.id)
            check(
                f"{company.name} can take payment",
                account is not None and account.charges_enabled,
                f"provider={account.provider}" if account else "no charges-enabled account",
            )

        section("Dates are anchored to today")
        past = db.query(ActivitySchedule).filter(ActivitySchedule.start_time < now).count()
        upcoming = db.query(ActivitySchedule).filter(ActivitySchedule.start_time >= now).count()
        check("history exists for reports", past >= 20, f"{past} past departures")
        check("upcoming work exists for dashboards", upcoming >= 20, f"{upcoming} upcoming")

        oldest = db.query(ActivitySchedule).order_by(ActivitySchedule.start_time).first()
        if oldest:
            age_days = (now - oldest.start_time).days
            check("nothing is stale", age_days <= 120, f"oldest departure {age_days} days ago")

        newest = (
            db.query(ActivitySchedule).order_by(ActivitySchedule.start_time.desc()).first()
        )
        if newest:
            ahead_days = (newest.start_time - now).days
            check("calendar extends into the future", ahead_days >= 30, f"{ahead_days} days ahead")

        print()
        if _failures:
            print(f"{len(_failures)} check(s) FAILED:")
            for f in _failures:
                print(f"  - {f}")
            print("\nThe demo is NOT ready. Re-run: python -m scripts.seed_demo --reset")
            return 1

        print("All checks passed — the demo is ready to show.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
