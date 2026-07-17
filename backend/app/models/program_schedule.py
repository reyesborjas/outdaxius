import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class ProgramSchedule(Base):
    __tablename__ = "program_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time   = Column(DateTime, nullable=False)
    price      = Column(Numeric(10,2))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    status = Column(String, default="pending", nullable=False)
    min_participants = Column(Integer, nullable=True)
    max_participants = Column(Integer, nullable=True)
    
      # valores: pending | confirmed | canceled

    program = relationship("Program", back_populates="schedules")
    activity_schedules = relationship(
        "ActivitySchedule",
        back_populates="program_schedule",
        cascade="all, delete-orphan"
    )
