# app/models/programactivity.py
import uuid
from sqlalchemy import Column, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class ProgramActivity(Base):
    __tablename__ = "programactivities"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    program_id = Column(UUID(as_uuid=True), ForeignKey("programs.id", ondelete="CASCADE"))
    activity_id = Column(UUID(as_uuid=True), ForeignKey("activities.id", ondelete="CASCADE"))

    __table_args__ = (
        UniqueConstraint("program_id", "activity_id", name="uq_program_activity"),
        Index("ix_programactivities_program_id", "program_id"),
        Index("ix_programactivities_activity_id", "activity_id"),
    )
