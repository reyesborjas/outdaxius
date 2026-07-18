# app/api/booking.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
from typing import List
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, BookingOut
from app.models.activity_schedule import ActivitySchedule
from app.models.program_schedule import ProgramSchedule
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentOut
from app.services.company_usage import companies_for_program_schedule, companies_for_activity_schedule
from app.services.enforce_limits import enforce_company_monthly_booking_limits
router = APIRouter()

@router.get("/", response_model=List[BookingOut])
def list_bookings(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    return db.query(Booking).filter(Booking.user_id == current.id).all()

@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    act_id = payload.activity_schedule_id
    prog_id = payload.program_schedule_id
    if bool(act_id) == bool(prog_id):
        raise HTTPException(400, "Provide exactly one of activity_schedule_id or program_schedule_id")

    participants = [p.model_dump() for p in payload.participants]
    seats_requested = len(participants)

    company_ids = set()

    if act_id:
        company_ids.update(companies_for_activity_schedule(db, act_id))

        # booking also carries program_schedule_id sometimes
        sched = db.query(ActivitySchedule).filter(ActivitySchedule.id == act_id).first()
        if sched and sched.program_schedule_id:
            company_ids.update(companies_for_program_schedule(db, sched.program_schedule_id))

    if prog_id:
        company_ids.update(companies_for_program_schedule(db, prog_id))

    for cid in company_ids:
        enforce_company_monthly_booking_limits(db, cid, seats_requested)
        
    if act_id:
        sched = db.query(ActivitySchedule).filter(ActivitySchedule.id == act_id).first()
        if not sched:
            raise HTTPException(404, "Activity schedule not found")

        exists = db.query(Booking).filter(
            Booking.user_id == current.id,
            Booking.activity_schedule_id == act_id
        ).first()
        if exists:
            raise HTTPException(409, "User already has a booking for this activity schedule")

        max_cap = sched.max_participants
        if max_cap is None and sched.program_schedule_id:
            parent = db.query(ProgramSchedule).filter(ProgramSchedule.id == sched.program_schedule_id).first()
            max_cap = parent.max_participants if parent else None

        if max_cap is not None:
            used = db.query(func.coalesce(func.sum(Booking.participants_count), 0)).filter(
                Booking.activity_schedule_id == act_id
            ).scalar()
            if seats_requested + used > max_cap:
                raise HTTPException(400, f"Not enough seats. Remaining: {max_cap - used}")

        booking = Booking(
            user_id=current.id,
            activity_schedule_id=sched.id,
            program_schedule_id=sched.program_schedule_id,
            status="pending",
            participants_count=seats_requested,
            participants=participants,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)
        return booking

    parent = db.query(ProgramSchedule).filter(ProgramSchedule.id == prog_id).first()
    if not parent:
        raise HTTPException(404, "Program schedule not found")

    exists = db.query(Booking).filter(
        Booking.user_id == current.id,
        Booking.program_schedule_id == prog_id
    ).first()
    if exists:
        raise HTTPException(409, "User already has a booking for this program schedule")

    max_cap = parent.max_participants
    if max_cap is not None:
        used = db.query(func.coalesce(func.sum(Booking.participants_count), 0)).filter(
            Booking.program_schedule_id == prog_id
        ).scalar()
        if seats_requested + used > max_cap:
            raise HTTPException(400, f"Not enough seats. Remaining: {max_cap - used}")

    booking = Booking(
        user_id=current.id,
        program_schedule_id=parent.id,
        status="pending",
        participants_count=seats_requested,
        participants=participants,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking

@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: uuid.UUID, db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current.id).first()
    if not b:
        raise HTTPException(404, "Booking not found")
    return b

@router.post("/{booking_id}/pay", response_model=PaymentOut, status_code=status.HTTP_201_CREATED)
def submit_payment(booking_id: uuid.UUID, payload: PaymentCreate,
                   db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current.id).first()
    if not b:
        raise HTTPException(404, "Booking not found")

    if b.status == "cancelled":
        raise HTTPException(400, "Cancelled booking cannot be paid")

    # Crea pago con estado pending y voucher_url (imagen de comprobante)
    p = Payment(
        booking_id=b.id,
        amount=payload.amount,
        currency=payload.currency or "USD",
        status="pending",
        voucher_url=str(payload.voucher_url) if payload.voucher_url else None,
        reference=payload.reference,
    )
    db.add(p)
    # Para el MVP, al enviar comprobante, marcamos el booking como "confirmed".
    b.status = "confirmed"
    db.add(b)
    db.commit()
    db.refresh(p)
    return p

@router.post("/{booking_id}/confirm-payment", response_model=BookingOut)
def confirm_payment(booking_id: uuid.UUID,
                    db: Session = Depends(get_db),
                    current: User = Depends(get_current_user)):
    # Simplificación: el mismo usuario puede confirmar. En producción: restringir a admin/operador.
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current.id).first()
    if not b:
        raise HTTPException(404, "Booking not found")
    if b.status == "cancelled":
        raise HTTPException(400, "Cannot confirm a cancelled booking")

    b.status = "confirmed"
    db.add(b)
    db.commit()
    db.refresh(b)
    return b

@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: uuid.UUID,
                   db: Session = Depends(get_db),
                   current: User = Depends(get_current_user)):
    b = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current.id).first()
    if not b:
        raise HTTPException(404, "Booking not found")

    if b.status == "cancelled":
        return b  # idempotente

    # Regla MVP: se puede cancelar siempre. En producción: ventana temporal y política de fee.
    b.status = "cancelled"
    db.add(b)
    db.commit()
    db.refresh(b)
    return b

@router.patch("/bookings/{booking_id}/participants/{participant_id}")
def edit_participant(booking_id: uuid.UUID, participant_id: str, updates: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current_user.id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    updated = False
    for participant in booking.participants:
        if participant['id'] == participant_id:
            participant.update(updates)
            updated = True
            # Log de auditoría aquí con los datos viejos y nuevos
    if updated:
        db.commit()
    else:
        raise HTTPException(404, "Participant not found")
    return booking