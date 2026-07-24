# app/models/activity.py
import uuid
from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, func, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class Activity(Base):
    __tablename__ = "activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    activity_type = Column(UUID(as_uuid=True), ForeignKey("types.id"), nullable=False)
    type = relationship("Types", foreign_keys=[activity_type])
   

    # relaciones
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=True)
    guide_leader = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Nullable: see app.models.programs.Program.team_id -- same Phase 2 backfill gap.
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    # Reuse policy: same team or same company may always schedule this; a different company may
    # only do so when this is true (app.core.permissions.check_can_reuse).
    is_shared = Column(Boolean, nullable=False, default=False)
    team = relationship("Team")

    @property
    def company_id(self):
        return self.team.company_id if self.team else None

    # datos adicionales
    gallery = Column(JSONB, nullable=False, server_default="[]")

    # timestamps
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now(), onupdate=func.now())

    # ORM relationships (sin importar schemas pydantic)
    location = relationship("Location", back_populates="activities")
    creator = relationship("User")
    leader = relationship("User", foreign_keys=[guide_leader])

    programs = relationship(
    "Program",
    secondary="programactivities",
    back_populates="activities",
)
    activity_schedules = relationship(
        "ActivitySchedule",
        back_populates="activity",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    type = relationship("Types", foreign_keys=[activity_type])
    location = relationship("Location", back_populates="activities")
    creator = relationship("User",foreign_keys=[created_by],back_populates="created_activities")  
    leader = relationship("User",foreign_keys=[guide_leader],back_populates="led_activities")
    programs = relationship("Program",secondary="programactivities",back_populates="activities",)
    activity_schedules = relationship("ActivitySchedule",back_populates="activity",   cascade="all, delete-orphan",passive_deletes=True,)