# app/models/programs.py
from sqlalchemy import Column, String, Text, JSON, Integer, ForeignKey, Boolean
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
    # Nullable: Phase 2's migration could only backfill this for rows whose creator was already
    # a team member. Rows with team_id IS NULL need manual assignment before anyone but a
    # platform admin can edit/delete them (see app.core.permissions).
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    # Reuse policy: same team or same company may always schedule this; a different company may
    # only do so when this is true (app.core.permissions.check_can_reuse).
    is_shared = Column(Boolean, nullable=False, default=False)

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