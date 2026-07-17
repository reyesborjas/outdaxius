# backend/app/schemas/company_limits.py
from pydantic import BaseModel
from typing import Optional, Dict
from uuid import UUID
from datetime import datetime

class LimitsOut(BaseModel):
    guides_max: Optional[int]
    max_activities: Optional[int]
    max_programs: Optional[int]
    max_schedules_total: Optional[int]
    max_monthly_bookings: Optional[int]
    max_monthly_participants: Optional[int]

class UsageOut(BaseModel):
    activities: int
    programs: int
    program_schedules: int
    activity_schedules: int
    schedules_total: int
    bookings: int
    participants: int

class MonthlyUsageOut(BaseModel):
    from_date: datetime
    to_date: datetime
    bookings: int
    participants: int

class CompanyLimitsResponse(BaseModel):
    company_id: UUID
    tier: str
    as_of: datetime
    limits: LimitsOut
    usage_historical: UsageOut
    usage_current_month: MonthlyUsageOut
