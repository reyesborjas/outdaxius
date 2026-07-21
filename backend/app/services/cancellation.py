# app/services/cancellation.py
"""
Cancellation policy, expressed in hours so "six days before" is never ambiguous. Fees are
deducted from the amount already paid -- never an additional charge. Frozen into
bookings.policy_snapshot at purchase time so a later policy change never alters a contract the
client already agreed to (spec 1.9).
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from app.models.booking import Booking
from app.models.user import User

CancelledByParty = Literal["client", "vendor", "system"]

# Percent of the amount paid that is RETAINED (not refunded) as a fee.
VENDOR_CANCEL_FEE_PCT = 0
CLIENT_168H_FEE_PCT = 0       # >= 168 hours (7 days) before start
CLIENT_24_168H_FEE_PCT = 70   # 24-168 hours before start
CLIENT_UNDER_24H_FEE_PCT = 100  # < 24 hours before start, or no-show

POLICY_VERSION = "2026-07-18"


def build_policy_snapshot() -> dict:
    """The active policy, frozen onto a booking at the moment of purchase (spec 1.9: "The active
    policy is frozen into bookings.policy_snapshot at purchase. Changing the policy later never
    alters a contract already agreed.")."""
    return {
        "policy_version": POLICY_VERSION,
        "vendor_cancel_fee_pct": VENDOR_CANCEL_FEE_PCT,
        "client_168h_fee_pct": CLIENT_168H_FEE_PCT,
        "client_24_168h_fee_pct": CLIENT_24_168H_FEE_PCT,
        "client_under_24h_fee_pct": CLIENT_UNDER_24H_FEE_PCT,
    }


def calculate_cancellation_fee(
    *,
    cancelled_by_party: CancelledByParty,
    hours_before_start: float,
    amount_paid: Decimal,
    policy_snapshot: dict | None = None,
) -> Decimal:
    """
    Vendor cancellation (or a declined reschedule, which counts as a vendor cancellation per spec
    1.9) is always a full refund -- the vendor absorbs the loss, never the client. Client
    cancellation follows the hour-tiered schedule. `policy_snapshot` lets a booking's OWN frozen
    terms govern instead of the current live constants, if provided.
    """
    snap = policy_snapshot or build_policy_snapshot()

    if cancelled_by_party in ("vendor", "system"):
        fee_pct = snap["vendor_cancel_fee_pct"]
    elif hours_before_start >= 168:
        fee_pct = snap["client_168h_fee_pct"]
    elif hours_before_start >= 24:
        fee_pct = snap["client_24_168h_fee_pct"]
    else:
        fee_pct = snap["client_under_24h_fee_pct"]

    return (amount_paid * Decimal(fee_pct) / Decimal(100)).quantize(Decimal("0.01"))


def apply_cancellation(
    *,
    booking: Booking,
    cancelled_by: User,
    cancelled_by_party: CancelledByParty,
    reason: Optional[str],
    amount_paid: Decimal,
    schedule_start: Optional[datetime],
) -> Decimal:
    """
    Shared bookkeeping for cancelling a booking, regardless of which payment path funded it
    (Flow, or the manual voucher-upload path). Stamps the cancellation fields on `booking` using
    its own frozen `policy_snapshot` and returns the computed refund_amount. Callers finish the
    job by deciding HOW the money actually moves -- an automated provider refund, or a manual
    bank transfer the vendor completes outside the platform -- and set `booking.refund_status`
    accordingly; this function never sets it, since "how" is provider-specific and "whether/how
    much" is not.
    """
    hours_before_start = 999999.0
    if schedule_start:
        now = datetime.now(schedule_start.tzinfo or timezone.utc)
        hours_before_start = (schedule_start - now).total_seconds() / 3600

    fee = calculate_cancellation_fee(
        cancelled_by_party=cancelled_by_party,
        hours_before_start=hours_before_start,
        amount_paid=amount_paid,
        policy_snapshot=booking.policy_snapshot or None,
    )
    refund_amount = amount_paid - fee

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.cancelled_by = cancelled_by.id
    booking.cancelled_by_party = cancelled_by_party
    booking.cancellation_reason = reason
    booking.cancellation_fee = fee
    booking.refund_amount = refund_amount
    return refund_amount
