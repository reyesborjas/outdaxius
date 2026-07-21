# backend/app/schemas/activity_schedule.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal
import uuid

class ActivityScheduleCreate(BaseModel):
    activity_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    program_schedule_id: Optional[uuid.UUID] = None
    min_participants: Optional[int] = None
    max_participants: Optional[int] = None
    price: Optional[Decimal] = None
    status: Literal["pending", "confirmed", "canceled"] = "pending"

class ActivityScheduleOut(BaseModel):
    id: uuid.UUID
    activity_id: uuid.UUID
    program_schedule_id: Optional[uuid.UUID]
    start_time: datetime
    end_time: datetime
    min_participants: Optional[int]
    max_participants: Optional[int]
    price: Optional[Decimal]
    status: Literal["pending", "confirmed", "canceled"]
    selling_company_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
