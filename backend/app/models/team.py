# app/models/team.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, String, DateTime, Text, SmallInteger, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name = Column(String, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    description = Column(Text, nullable=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    # Spec 1.7 departure guard: set False when a level-1 guide leaves an otherwise-empty team
    # (app.services.team_departure.leave_team) rather than leaving it dangling with zero members.
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])
    company = relationship("Company")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    # Cascading hierarchy, lower number = more power. 1 master, 2 planner, 3 coordinator,
    # 4 field guide. Every capability at level N is also held by every level below N.
    role_level = Column(SmallInteger, nullable=False, default=4)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint("role_level BETWEEN 1 AND 4", name="ck_team_members_role_level"),
    )

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("User")





    
