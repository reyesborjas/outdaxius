# app/models/activity_schedule.py
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base



class ActivitySchedule(Base):
    __tablename__ = "activity_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    program_schedule_id = Column(UUID(as_uuid=True), ForeignKey("program_schedules.id", ondelete="CASCADE"), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time   = Column(DateTime, nullable=False)
    price      = Column(Numeric(10,2))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    activity = relationship("Activity", back_populates="activity_schedules")
    program_schedule = relationship("ProgramSchedule", back_populates="activity_schedules")
    status = Column(String, default="pending", nullable=False)
    min_participants = Column(Integer, nullable=True)
    max_participants = Column(Integer, nullable=True)
      # valores: pending | confirmed | canceled

    # Added by the Phase 2 migration but not previously mapped on the ORM.
    selling_company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=True)