# app/models/booking.py
import uuid
from sqlalchemy import Column, ForeignKey, String, DateTime, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    program_schedule_id  = Column(UUID(as_uuid=True), ForeignKey("program_schedules.id", ondelete="CASCADE"), nullable=True)
    activity_schedule_id = Column(UUID(as_uuid=True), ForeignKey("activity_schedules.id", ondelete="CASCADE"), nullable=True)

    status = Column(String, default="pending")          # pending | confirmed | cancelled
    # NOT NULL DEFAULT 'not_attended' since the Phase 2 migration -- the Python-side default
    # matters because SQLAlchemy sends an explicit NULL on insert otherwise, which overrides the
    # server-side DEFAULT and violates the NOT NULL constraint.
    attendance_status = Column(String, nullable=False, default="not_attended")

    participants_count = Column(Integer, nullable=False, default=1)
    # [{first_name,last_name,id_type,id_number,birth_date}]
    participants = Column(JSONB, nullable=False, default=list)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    cancelled_at = Column(DateTime, nullable=True)
    # DB column is numeric(12,2), matching refund_amount below -- was declared Integer here, which
    # silently truncates cents on write (SQLAlchemy's Integer bind processor calls int() on the
    # Decimal fee before sending it).
    cancellation_fee = Column(Numeric(12, 2), nullable=True)

    # Added by the Phase 2 migration but not previously mapped on the ORM -- Phase 4 is the first
    # phase that actually reads/writes them.
    cancelled_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    cancelled_by_party = Column(String, nullable=True)  # client | vendor | system
    cancellation_reason = Column(String, nullable=True)
    refund_amount = Column(Numeric(12, 2), nullable=True)
    refund_status = Column(String, nullable=True)  # not_required | pending | succeeded | failed | manual
    refund_reference = Column(String, nullable=True)
    # Cancellation policy frozen at purchase time (see app.services.cancellation) so a later
    # policy change never alters a contract the client already agreed to.
    policy_snapshot = Column(JSONB, nullable=False, default=dict)

