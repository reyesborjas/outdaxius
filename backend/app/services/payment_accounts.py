# app/services/payment_accounts.py
"""
Shared helpers for resolving which company, and which payment-provider account, funds a booking.
Promoted out of payments_flow.py so booking.py's cancel_booking can also attempt an automated
refund (Flow/demo) without importing that module's "private" helpers or duplicating the logic.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.activity_schedule import ActivitySchedule
from app.models.program_schedule import ProgramSchedule
from app.models.company_payment_account import CompanyPaymentAccount


def resolve_selling_company_id(db: Session, booking: Booking) -> Optional[UUID]:
    if booking.activity_schedule_id:
        sched = db.query(ActivitySchedule).filter(ActivitySchedule.id == booking.activity_schedule_id).first()
        if sched:
            if sched.selling_company_id:
                return sched.selling_company_id
            if sched.program_schedule_id:
                parent = db.query(ProgramSchedule).filter(ProgramSchedule.id == sched.program_schedule_id).first()
                if parent:
                    return parent.selling_company_id
    if booking.program_schedule_id:
        parent = db.query(ProgramSchedule).filter(ProgramSchedule.id == booking.program_schedule_id).first()
        if parent:
            return parent.selling_company_id
    return None


def get_payment_account(db: Session, company_id: UUID, provider: str) -> Optional[CompanyPaymentAccount]:
    return db.query(CompanyPaymentAccount).filter(
        CompanyPaymentAccount.company_id == company_id,
        CompanyPaymentAccount.provider == provider,
    ).first()


def get_any_charges_enabled_account(db: Session, company_id: UUID) -> Optional[CompanyPaymentAccount]:
    """For the generic 'Pay Now' button: whichever provider this company has verified, first
    match wins -- a demo/pitch company realistically has exactly one configured."""
    return db.query(CompanyPaymentAccount).filter(
        CompanyPaymentAccount.company_id == company_id,
        CompanyPaymentAccount.charges_enabled == True,  # noqa: E712
    ).first()
