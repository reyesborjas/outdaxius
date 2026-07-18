# app/models/assignment.py
import uuid
from sqlalchemy import Column, ForeignKey, String, Boolean, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class Assignment(Base):
    """
    Which guide executes which activity schedule, and whose company invoices.
    home_company_id != the schedule's selling_company_id is the entire definition of an external
    guide — no membership is disturbed, and the "open window" is the schedule's own date range.
    """
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity_schedule_id = Column(
        UUID(as_uuid=True), ForeignKey("activity_schedules.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    home_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False)
    home_company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False)
    is_leader = Column(Boolean, nullable=False, default=False)
    status = Column(String, nullable=False, default="proposed")
    proposed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    proposed_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)
    decline_reason = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'accepted', 'rejected', 'cancelled')",
            name="ck_assignments_status",
        ),
        UniqueConstraint("activity_schedule_id", "user_id", name="uq_assignment_once"),
    )
