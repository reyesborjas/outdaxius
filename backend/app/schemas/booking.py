# app/schemas/booking.py
import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class BookingParticipant(BaseModel):
    first_name: str
    last_name: str
    id_type: Literal["national_id", "passport"]
    id_number: str
    birth_date: str  # YYYY-MM-DD

class BookingCreate(BaseModel):
    activity_schedule_id: Optional[uuid.UUID] = None
    program_schedule_id: Optional[uuid.UUID] = None
    participants: List[BookingParticipant] = Field(min_length=1)

class BookingCancelRequest(BaseModel):
    reason: Optional[str] = None

class BookingOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    activity_schedule_id: Optional[uuid.UUID] = None
    program_schedule_id: Optional[uuid.UUID] = None
    status: str
    attendance_status: Optional[str] = None
    participants_count: int
    participants: List[BookingParticipant]
    cancelled_at: Optional[datetime] = None
    cancelled_by_party: Optional[str] = None
    cancellation_reason: Optional[str] = None
    cancellation_fee: Optional[Decimal] = None
    refund_amount: Optional[Decimal] = None
    refund_status: Optional[str] = None

    class Config:
        from_attributes = True
