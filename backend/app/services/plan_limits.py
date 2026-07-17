# backend/app/services/plan_limits.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict

def normalize_tier(raw: Optional[str]) -> str:
    t = (raw or "").strip().lower()
    if t in ("free", "basic"):
        return "basic"
    if t in ("pro", "enterprise"):
        return t
    return "basic"

@dataclass(frozen=True)
class PlanLimits:
    # None = unlimited
    max_activities: Optional[int]
    max_programs: Optional[int]
    max_schedules_total: Optional[int]          # program_schedules + activity_schedules
    max_monthly_bookings: Optional[int]
    max_monthly_participants: Optional[int]

LIMITS_BY_TIER: Dict[str, PlanLimits] = {
    # You can tune these numbers anytime without DB changes
    "basic": PlanLimits(
        max_activities=20,
        max_programs=10,
        max_schedules_total=50,
        max_monthly_bookings=100,
        max_monthly_participants=300,
    ),
    "pro": PlanLimits(
        max_activities=500,
        max_programs=200,
        max_schedules_total=2000,
        max_monthly_bookings=2000,
        max_monthly_participants=6000,
    ),
    "enterprise": PlanLimits(
        max_activities=None,
        max_programs=None,
        max_schedules_total=None,
        max_monthly_bookings=None,
        max_monthly_participants=None,
    ),
}

def get_limits_for_tier(raw_tier: Optional[str]) -> PlanLimits:
    tier = normalize_tier(raw_tier)
    return LIMITS_BY_TIER.get(tier, LIMITS_BY_TIER["basic"])
