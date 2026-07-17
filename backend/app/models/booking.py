# app/models/booking.py
import uuid
from sqlalchemy import Column, ForeignKey, String, DateTime, Integer
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
    attendance_status = Column(String, nullable=True)   # attended | no-show

    participants_count = Column(Integer, nullable=False, default=1)
    # [{first_name,last_name,id_type,id_number,birth_date}]
    participants = Column(JSONB, nullable=False, default=list)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    cancelled_at = Column(DateTime, nullable=True)
    cancellation_fee = Column(Integer, nullable=True)

