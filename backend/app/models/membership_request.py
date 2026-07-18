# app/models/membership_request.py
import uuid
from sqlalchemy import Column, ForeignKey, String, Text, SmallInteger, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base


class MembershipRequest(Base):
    """
    Invitations and applications share one state machine, differing only by direction and by who
    is required to accept. on_behalf_of_company_id is set when a company officer postulates
    somebody other than themselves — that case is three-party: officer proposes, guide consents
    via target_consent, host team accepts.
    """
    __tablename__ = "membership_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    direction = Column(String, nullable=False)  # invitation | application
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"), nullable=False)
    target_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    target_email = Column(Text, nullable=True)
    offered_level = Column(SmallInteger, nullable=False, default=4)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    on_behalf_of_company_id = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=True)
    target_consent = Column(String, nullable=False, default="not_required")
    message = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("direction IN ('invitation', 'application')", name="ck_membership_requests_direction"),
        CheckConstraint("offered_level BETWEEN 1 AND 4", name="ck_membership_requests_level"),
        CheckConstraint(
            "status IN ('pending','accepted','rejected','cancelled','expired')",
            name="ck_membership_requests_status",
        ),
        CheckConstraint(
            "target_consent IN ('not_required','pending','granted','refused')",
            name="ck_membership_requests_consent",
        ),
        CheckConstraint(
            "target_user_id IS NOT NULL OR target_email IS NOT NULL",
            name="ck_membership_requests_target",
        ),
    )
