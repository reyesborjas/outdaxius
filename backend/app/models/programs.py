# app/models/programs.py
from sqlalchemy import Column, String, Text, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base
import uuid
from sqlalchemy.orm import relationship

class Program(Base):
    __tablename__ = "programs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text)
    gallery = Column(JSON, default=[])
    min_activities = Column(Integer, default=2)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    guide_leader = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  
    created_at = Column(Text, default=func.now())
    updated_at = Column(Text, default=func.now())
    program_type = Column(UUID(as_uuid=True), ForeignKey("types.id"), nullable=False)
    
    # Relationships
    type = relationship("Types", foreign_keys=[program_type])
    creator = relationship("User",foreign_keys=[created_by],back_populates="created_programs")
    leader = relationship("User", foreign_keys=[guide_leader],back_populates="led_programs")  
    
    activities = relationship(
        "Activity",
        secondary="programactivities",
        back_populates="programs"
    )

    schedules = relationship(
        "ProgramSchedule",
        back_populates="program",
        cascade="all, delete-orphan"
    )