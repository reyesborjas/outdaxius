# app/services/vendor_reputation.py
"""
Vendor cancellation-rate: how often a company cancels ON travelers (never the reverse), published
so travelers can see it before booking. User's explicit design call: vendor-initiated
cancellations only (cancelled_by_party == "vendor") -- a client cancelling their own trip isn't a
mark against the vendor's reliability -- over a rolling 90-day window, scoped by booking creation
time so the number reflects recent volume/behavior rather than ancient history.
"""
from datetime import datetime, timedelta, timezone
from typing import TypedDict
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.activity_schedule import ActivitySchedule
from app.models.program_schedule import ProgramSchedule
from app.models.booking import Booking

WINDOW_DAYS = 90
# Below this many bookings in the window, a rate is too noisy to publish -- a single cancellation
# out of one booking would otherwise show as "100% cancellation rate" for a brand-new vendor.
MIN_SAMPLE_SIZE = 5


class CancellationRate(TypedDict):
    cancellation_rate: float | None
    vendor_cancellations: int
    total_bookings: int
    window_days: int
    sufficient_data: bool


def _company_bookings_query(db: Session, company_id: UUID, cutoff: datetime):
    """Every booking whose schedule sells for this company -- either the activity_schedule sells
    directly, or it inherits selling_company_id from its parent program_schedule (see
    activity_schedules.create_activity_schedule), or it's a direct program_schedule booking."""
    act_sched_ids = (
        db.query(ActivitySchedule.id)
        .outerjoin(ProgramSchedule, ActivitySchedule.program_schedule_id == ProgramSchedule.id)
        .filter(
            or_(
                ActivitySchedule.selling_company_id == company_id,
                ProgramSchedule.selling_company_id == company_id,
            )
        )
    )
    prog_sched_ids = db.query(ProgramSchedule.id).filter(ProgramSchedule.selling_company_id == company_id)

    return db.query(Booking).filter(
        Booking.created_at >= cutoff,
        or_(
            Booking.activity_schedule_id.in_(act_sched_ids),
            Booking.program_schedule_id.in_(prog_sched_ids),
        ),
    )


def get_vendor_cancellation_rate(
    db: Session, company_id: UUID, window_days: int = WINDOW_DAYS
) -> CancellationRate:
    # Booking.created_at is a naive DateTime column (no timezone=True) -- match it with a naive
    # UTC cutoff rather than an aware one, or the comparison silently returns wrong results.
    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).replace(tzinfo=None)
    q = _company_bookings_query(db, company_id, cutoff)

    total = q.count()
    vendor_cancelled = q.filter(
        Booking.status == "cancelled", Booking.cancelled_by_party == "vendor"
    ).count()

    sufficient = total >= MIN_SAMPLE_SIZE
    rate = round(vendor_cancelled / total, 4) if sufficient else None

    return {
        "cancellation_rate": rate,
        "vendor_cancellations": vendor_cancelled,
        "total_bookings": total,
        "window_days": window_days,
        "sufficient_data": sufficient,
    }
