# app/api/payments_flow.py
"""
The automated (Flow, card) payment path -- separate from booking.py's manual voucher-upload path.
A booking only becomes `confirmed` here once the webhook independently re-queries the provider's
authoritative status; the client's own request never confirms a booking by itself.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
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
from app.services.cancellation import calculate_cancellation_fee

router = APIRouter(tags=["payments-flow"])


def _resolve_selling_company_id(db: Session, booking: Booking) -> Optional[UUID]:
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


def _get_flow_account(db: Session, company_id: UUID) -> CompanyPaymentAccount:
    account = db.query(CompanyPaymentAccount).filter(
        CompanyPaymentAccount.company_id == company_id,
        CompanyPaymentAccount.provider == "flow",
    ).first()
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
    if booking.user_id != current.id and current.role != "admin":
        raise HTTPException(403, detail="Not allowed")

    payment = db.query(Payment).filter(
        Payment.booking_id == booking_id, Payment.provider == "flow", Payment.status == "succeeded"
    ).first()
    if not payment:
        raise HTTPException(400, detail="No succeeded Flow payment to refund for this booking")

    selling_company_id = _resolve_selling_company_id(db, booking)
    if not selling_company_id:
        raise HTTPException(400, detail="Cannot resolve the company for this booking")
    account = _get_flow_account(db, selling_company_id)
    provider = get_provider(account)

    schedule = None
    if booking.activity_schedule_id:
        schedule = db.query(ActivitySchedule).filter(ActivitySchedule.id == booking.activity_schedule_id).first()
    elif booking.program_schedule_id:
        schedule = db.query(ProgramSchedule).filter(ProgramSchedule.id == booking.program_schedule_id).first()

    hours_before_start = 999999.0
    if schedule and schedule.start_time:
        now = datetime.now(schedule.start_time.tzinfo or timezone.utc)
        hours_before_start = (schedule.start_time - now).total_seconds() / 3600

    fee = calculate_cancellation_fee(
        cancelled_by_party=payload.cancelled_by_party,
        hours_before_start=hours_before_start,
        amount_paid=payment.amount,
        policy_snapshot=booking.policy_snapshot or None,
    )
    refund_amount = payment.amount - fee

    result = provider.refund(payment.provider_ref, refund_amount)

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    booking.cancelled_by = current.id
    booking.cancelled_by_party = payload.cancelled_by_party
    booking.cancellation_reason = payload.reason
    booking.cancellation_fee = fee
    booking.refund_amount = refund_amount

    if result.success:
        booking.refund_status = "succeeded"
        booking.refund_reference = result.provider_refund_ref
        payment.status = "refunded" if fee == 0 else "partially_refunded"
    else:
        # Spec: insufficient vendor balance (or any provider failure) is routine, not an error --
        # queue it for manual resolution rather than surfacing a 500 to the client.
        booking.refund_status = "manual"

    db.commit()
    return {
        "status": "ok",
        "refund_status": booking.refund_status,
        "refund_amount": str(refund_amount),
        "fee": str(fee),
    }


class ManualQueueItem(BaseModel):
    booking_id: UUID
    user_id: UUID
    cancelled_at: Optional[datetime] = None
    refund_amount: Optional[Decimal] = None
    cancellation_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


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
        return bookings

    return query.all()


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
