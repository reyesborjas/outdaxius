# backend/app/services/enforce_limits.py
from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.company_payment_account import CompanyPaymentAccount
from app.services.plan_limits import get_limits_for_tier
from app.services.company_usage import historical_usage, monthly_usage, month_window_utc

def _limit_or_ok(current: int, limit: int | None) -> bool:
    return (limit is None) or (current < limit)

def enforce_company_creation_limits(db: Session, company_id: UUID, metric: str):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(404, detail="Company not found")

    limits = get_limits_for_tier(company.license_tier)
    usage = historical_usage(db, company_id)

    if metric == "activities":
        lim = limits.max_activities
        cur = usage["activities"]
    elif metric == "programs":
        lim = limits.max_programs
        cur = usage["programs"]
    elif metric == "schedules_total":
        lim = limits.max_schedules_total
        cur = usage["schedules_total"]
    else:
        raise HTTPException(500, detail="Unknown metric")

    if lim is not None and cur >= lim:
        raise HTTPException(
            402,
            detail=f"Plan limit reached for {metric}: {cur}/{lim}. Upgrade to increase capacity."
        )

def enforce_charges_enabled(db: Session, company_id: UUID):
    """
    A company cannot publish a sellable schedule until it has completed payment onboarding
    (company_payment_accounts.charges_enabled = true for at least one provider). This state did
    not exist in the app before Phase 4 -- see app/api/company_payments.py for the onboarding
    endpoints that set it.
    """
    has_charges_enabled = db.query(CompanyPaymentAccount).filter(
        CompanyPaymentAccount.company_id == company_id,
        CompanyPaymentAccount.charges_enabled == True,  # noqa: E712
    ).first()
    if not has_charges_enabled:
        raise HTTPException(
            402,
            detail="This company must complete payment onboarding (a verified payment account) "
                   "before publishing a sellable schedule."
        )


def enforce_company_monthly_booking_limits(db: Session, company_id: UUID, seats_requested: int):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        return  # ignore if company missing (shouldn't happen)

    limits = get_limits_for_tier(company.license_tier)
    start, end = month_window_utc(datetime.now(timezone.utc))
    mu = monthly_usage(db, company_id, start, end)

    # bookings
    if limits.max_monthly_bookings is not None and mu["bookings"] >= limits.max_monthly_bookings:
        raise HTTPException(
            402,
            detail=f"Company monthly booking limit reached: {mu['bookings']}/{limits.max_monthly_bookings}."
        )

    # participants
    if limits.max_monthly_participants is not None and (mu["participants"] + seats_requested) > limits.max_monthly_participants:
        raise HTTPException(
            402,
            detail=(
                f"Company monthly participants limit reached: "
                f"{mu['participants']}/{limits.max_monthly_participants} (trying to add {seats_requested})."
            )
        )
