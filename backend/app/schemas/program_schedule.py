# app/schemas/program_schedule.py
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

class ProgramScheduleCreate(BaseModel):
    program_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    price: Optional[float] = None

class ProgramScheduleOut(BaseModel):
    id: uuid.UUID
    program_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    price: Optional[float]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
