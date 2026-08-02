# app/api/payments_flow.py
"""
The automated (Flow, card) payment path -- separate from booking.py's manual voucher-upload path.
A booking only becomes `confirmed` here once the webhook independently re-queries the provider's
authoritative status; the client's own request never confirms a booking by itself.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.core.permissions import check_company_admin
from app.models.user import User
from app.models.booking import Booking
from app.models.payment import Payment
from app.models.activity_schedule import ActivitySchedule
from app.models.program_schedule import ProgramSchedule
from app.models.company_payment_account import CompanyPaymentAccount
from app.models.companymember import CompanyMember
from app.services.payments.base import get_provider
from app.services.cancellation import apply_cancellation
from app.services.payment_accounts import (
    resolve_selling_company_id,
    get_payment_account,
    get_any_charges_enabled_account,
)

router = APIRouter(tags=["payments-flow"])


def _resolve_selling_company_id(db: Session, booking: Booking) -> Optional[UUID]:
    return resolve_selling_company_id(db, booking)


def _get_flow_account(db: Session, company_id: UUID) -> CompanyPaymentAccount:
    account = get_payment_account(db, company_id, "flow")
    if not account:
        raise HTTPException(400, detail="This company has no Flow payment account configured.")
    return account


def _is_refund_admin(db: Session, user: User, company_id: Optional[UUID]) -> bool:
    if user.role == "admin":
        return True
    if company_id is None:
        return False
    return check_company_admin(db, user, company_id)


class FlowPayResponse(BaseModel):
    payment_id: UUID
    redirect_url: str


@router.post("/bookings/{booking_id}/pay/flow", response_model=FlowPayResponse, status_code=status.HTTP_201_CREATED)
def pay_with_flow(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current.id).first()
    if not booking:
        raise HTTPException(404, detail="Booking not found")
    if booking.status == "cancelled":
        raise HTTPException(400, detail="Cancelled booking cannot be paid")

    selling_company_id = _resolve_selling_company_id(db, booking)
    if not selling_company_id:
        raise HTTPException(400, detail="This booking's schedule has no resolved selling company; cannot charge.")

    account = _get_flow_account(db, selling_company_id)
    if not account.charges_enabled:
        raise HTTPException(400, detail="This company's Flow account is not yet verified.")

    schedule = None
    if booking.activity_schedule_id:
        schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == booking.activity_schedule_id).first()
    elif booking.program_schedule_id:
        schedule = db.query(ProgramSchedule).filter(ProgramSchedule.id == booking.program_schedule_id).first()
    if not schedule or schedule.price is None:
        raise HTTPException(400, detail="Schedule has no price set.")

    amount = Decimal(schedule.price) * booking.participants_count

    provider = get_provider(account)
    result = provider.create_payment(
        booking_id=str(booking.id),
        amount=amount,
        currency=account.currency,
        return_url=f"/bookings/{booking.id}",
        confirmation_url="/api/webhooks/flow",
    )

    payment = Payment(
        booking_id=booking.id,
        amount=amount,
        currency=account.currency,
        status="pending",
        provider="flow",
        provider_ref=result.provider_ref,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return FlowPayResponse(payment_id=payment.id, redirect_url=result.redirect_url)


class PayResponse(BaseModel):
    payment_id: UUID
    provider: str
    redirect_url: str


@router.post("/bookings/{booking_id}/pay", response_model=PayResponse, status_code=status.HTTP_201_CREATED)
def pay_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    Provider-agnostic pay endpoint: resolves whichever charges-enabled account the selling
    company has configured (Flow, demo, or a future provider) rather than hardcoding one, so the
    frontend needs exactly one "Pay Now" button regardless of what the company set up. Same
    create_payment/Payment-row logic as pay_with_flow above, just not Flow-specific.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current.id).first()
    if not booking:
        raise HTTPException(404, detail="Booking not found")
    if booking.status == "cancelled":
        raise HTTPException(400, detail="Cancelled booking cannot be paid")

    selling_company_id = resolve_selling_company_id(db, booking)
    if not selling_company_id:
        raise HTTPException(400, detail="This booking's schedule has no resolved selling company; cannot charge.")

    account = get_any_charges_enabled_account(db, selling_company_id)
    if not account:
        raise HTTPException(
            400,
            detail="This company has no verified automated payment account. Use the manual "
                   "voucher option instead.",
        )

    schedule = None
    if booking.activity_schedule_id:
        schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == booking.activity_schedule_id).first()
    elif booking.program_schedule_id:
        schedule = db.query(ProgramSchedule).filter(ProgramSchedule.id == booking.program_schedule_id).first()
    if not schedule or schedule.price is None:
        raise HTTPException(400, detail="Schedule has no price set.")

    amount = Decimal(schedule.price) * booking.participants_count

    provider = get_provider(account)
    result = provider.create_payment(
        booking_id=str(booking.id),
        amount=amount,
        currency=account.currency,
        return_url=f"/bookings/{booking.id}",
        confirmation_url=f"/api/webhooks/{account.provider}",
    )

    payment = Payment(
        booking_id=booking.id,
        amount=amount,
        currency=account.currency,
        status="pending",
        provider=account.provider,
        provider_ref=result.provider_ref,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return PayResponse(payment_id=payment.id, provider=account.provider, redirect_url=result.redirect_url)


class DemoPaymentOut(BaseModel):
    payment_id: UUID
    booking_id: UUID
    amount: Decimal
    currency: str
    status: str
    schedule_title: Optional[str] = None


def _demo_payment_for_owner(db: Session, provider_ref: str, current: User) -> tuple[Payment, Booking]:
    payment = db.query(Payment).filter(Payment.provider == "demo", Payment.provider_ref == provider_ref).first()
    booking = db.query(Booking).filter(Booking.id == payment.booking_id).first() if payment else None
    # Same 404 regardless of "doesn't exist" vs "not yours" -- don't leak which one it is.
    if not payment or not booking or (booking.user_id != current.id and current.role != "admin"):
        raise HTTPException(404, detail="Payment not found")
    return payment, booking


def _schedule_title(db: Session, booking: Booking) -> Optional[str]:
    if booking.activity_schedule_id:
        sched = db.query(ActivitySchedule).filter(ActivitySchedule.id == booking.activity_schedule_id).first()
        if sched:
            from app.models.activity import Activity
            activity = db.query(Activity).filter(Activity.id == sched.activity_id).first()
            return activity.title if activity else None
    elif booking.program_schedule_id:
        sched = db.query(ProgramSchedule).filter(ProgramSchedule.id == booking.program_schedule_id).first()
        if sched:
            from app.models.programs import Program
            program = db.query(Program).filter(Program.id == sched.program_id).first()
            return program.title if program else None
    return None


@router.get("/payments/demo/{provider_ref}", response_model=DemoPaymentOut)
def get_demo_payment(
    provider_ref: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Backs the simulated checkout page (frontend route /demo-checkout/:providerRef)."""
    payment, booking = _demo_payment_for_owner(db, provider_ref, current)
    return DemoPaymentOut(
        payment_id=payment.id,
        booking_id=booking.id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        schedule_title=_schedule_title(db, booking),
    )


class DemoCompleteRequest(BaseModel):
    outcome: Literal["succeeded", "failed"] = "succeeded"


@router.post("/payments/demo/{provider_ref}/complete", response_model=DemoPaymentOut)
def complete_demo_payment(
    provider_ref: str,
    payload: DemoCompleteRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """
    The demo's stand-in for a real webhook: a direct, authenticated action by the booking's own
    owner (clicking "Pay" or "Decline" on the simulated checkout page), not an unauthenticated
    callback -- there's no external party to call back from. Mirrors flow_webhook's effect on
    success (booking -> confirmed) so the rest of the app can't tell the difference.
    """
    payment, booking = _demo_payment_for_owner(db, provider_ref, current)
    if payment.status != "pending":
        raise HTTPException(400, detail=f"Payment already {payment.status}")

    payment.status = payload.outcome
    if payload.outcome == "succeeded":
        booking.status = "confirmed"
    db.commit()
    db.refresh(payment)

    return DemoPaymentOut(
        payment_id=payment.id,
        booking_id=booking.id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        schedule_title=_schedule_title(db, booking),
    )


@router.post("/webhooks/flow")
async def flow_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Confirmation callback. NEVER trusts the callback body for the actual outcome -- verifies the
    signature to establish this really came from Flow, then re-queries get_status(), the only
    authoritative source, exactly per the spec's instruction.
    """
    from urllib.parse import parse_qsl

    raw_body = await request.body()
    fields = dict(parse_qsl(raw_body.decode("utf-8")))
    token = fields.get("token")
    if not token:
        raise HTTPException(400, detail="Missing token")

    payment = db.query(Payment).filter(Payment.provider == "flow", Payment.provider_ref == token).first()
    if not payment:
        # Don't leak whether a token is valid/invalid beyond a generic 404 -- also handles
        # Flow retrying a webhook for a payment we've since reconciled some other way.
        raise HTTPException(404, detail="Unknown payment reference")

    booking = db.query(Booking).filter(Booking.id == payment.booking_id).first()
    selling_company_id = _resolve_selling_company_id(db, booking) if booking else None
    if not selling_company_id:
        raise HTTPException(400, detail="Cannot resolve the company for this payment")

    account = _get_flow_account(db, selling_company_id)
    provider = get_provider(account)

    if not provider.verify_webhook_signature(raw_body, dict(request.headers)):
        raise HTTPException(400, detail="Invalid webhook signature")

    # Authoritative re-query -- the callback body itself is never trusted for the outcome.
    result = provider.get_status(token)
    payment.status = result.status

    if result.status == "succeeded" and booking:
        booking.status = "confirmed"

    db.commit()
    return {"status": "ok"}


class RefundRequest(BaseModel):
    cancelled_by_party: str  # client | vendor | system
    reason: Optional[str] = None


@router.post("/bookings/{booking_id}/refund", response_model=dict)
def refund_booking(
    booking_id: UUID,
    payload: RefundRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, detail="Booking not found")
    is_admin = current.role == "admin"
    if booking.user_id != current.id and not is_admin:
        raise HTTPException(403, detail="Not allowed")

    # Only an admin may declare a non-client party -- otherwise a client cancelling their own
    # booking could claim cancelled_by_party="vendor" to dodge the client fee tiers entirely
    # (vendor cancellations are always a full refund per spec 1.9).
    cancelled_by_party = payload.cancelled_by_party if is_admin else "client"

    payment = db.query(Payment).filter(
        Payment.booking_id == booking_id, Payment.provider.isnot(None), Payment.status == "succeeded"
    ).first()
    if not payment:
        raise HTTPException(400, detail="No succeeded automated payment to refund for this booking")

    selling_company_id = resolve_selling_company_id(db, booking)
    if not selling_company_id:
        raise HTTPException(400, detail="Cannot resolve the company for this booking")
    account = get_payment_account(db, selling_company_id, payment.provider)
    if not account:
        raise HTTPException(400, detail=f"This company has no {payment.provider} payment account configured.")
    provider = get_provider(account)

    schedule = None
    if booking.activity_schedule_id:
        schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == booking.activity_schedule_id).first()
    elif booking.program_schedule_id:
        schedule = db.query(ProgramSchedule).filter(ProgramSchedule.id == booking.program_schedule_id).first()

    refund_amount = apply_cancellation(
        booking=booking,
        cancelled_by=current,
        cancelled_by_party=cancelled_by_party,
        reason=payload.reason,
        amount_paid=payment.amount,
        schedule_start=schedule.start_time if schedule else None,
    )

    result = provider.refund(payment.provider_ref, refund_amount)

    if result.success:
        booking.refund_status = "succeeded"
        booking.refund_reference = result.provider_refund_ref
        payment.status = "refunded" if booking.cancellation_fee == 0 else "partially_refunded"
    else:
        # Spec: insufficient vendor balance (or any provider failure) is routine, not an error --
        # queue it for manual resolution rather than surfacing a 500 to the client.
        booking.refund_status = "manual"

    db.commit()
    return {
        "status": "ok",
        "refund_status": booking.refund_status,
        "refund_amount": str(refund_amount),
        "fee": str(booking.cancellation_fee),
    }


class ManualQueueItem(BaseModel):
    booking_id: UUID
    user_id: UUID
    cancelled_at: Optional[datetime] = None
    refund_amount: Optional[Decimal] = None
    cancellation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


def _to_manual_queue_item(b: Booking) -> ManualQueueItem:
    return ManualQueueItem(
        booking_id=b.id,
        user_id=b.user_id,
        cancelled_at=b.cancelled_at,
        refund_amount=b.refund_amount,
        cancellation_reason=b.cancellation_reason,
    )


@router.get("/admin/refunds/manual-queue", response_model=List[ManualQueueItem])
def list_manual_refund_queue(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = db.query(Booking).filter(Booking.refund_status == "manual")

    if current.role != "admin":
        # Company admins only see bookings belonging to a company they administer.
        admin_company_ids = {
            m.companyid for m in db.query(CompanyMember).filter(
                CompanyMember.userid == current.id,
                CompanyMember.is_admin == True,  # noqa: E712
                CompanyMember.is_active == True,  # noqa: E712
            ).all()
        }
        if not admin_company_ids:
            raise HTTPException(403, detail="Not a company admin")
        bookings = [b for b in query.all() if _resolve_selling_company_id(db, b) in admin_company_ids]
        return [_to_manual_queue_item(b) for b in bookings]

    return [_to_manual_queue_item(b) for b in query.all()]


class ResolveRefundRequest(BaseModel):
    outcome: str  # succeeded | failed
    note: Optional[str] = None


@router.post("/admin/refunds/{booking_id}/resolve", response_model=dict)
def resolve_manual_refund(
    booking_id: UUID,
    payload: ResolveRefundRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if payload.outcome not in ("succeeded", "failed"):
        raise HTTPException(400, detail="outcome must be 'succeeded' or 'failed'")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, detail="Booking not found")

    selling_company_id = _resolve_selling_company_id(db, booking)
    if not _is_refund_admin(db, current, selling_company_id):
        raise HTTPException(403, detail="Not allowed")

    if booking.refund_status != "manual":
        raise HTTPException(400, detail="This booking is not in the manual refund queue")

    booking.refund_status = payload.outcome
    if payload.note:
        booking.cancellation_reason = f"{booking.cancellation_reason or ''}\n[refund resolution] {payload.note}".strip()
    db.commit()
    return {"status": "ok", "refund_status": booking.refund_status}
