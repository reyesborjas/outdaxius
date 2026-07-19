# app/services/cancellation.py
"""
Cancellation policy, expressed in hours so "six days before" is never ambiguous. Fees are
deducted from the amount already paid -- never an additional charge. Frozen into
bookings.policy_snapshot at purchase time so a later policy change never alters a contract the
client already agreed to (spec 1.9).
"""
from decimal import Decimal
from typing import Literal

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
