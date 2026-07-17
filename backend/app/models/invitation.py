# app/models/invitation.py
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class InvitationCode(Base):
    __tablename__ = "invitation_codes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(Text, unique=True, nullable=False, index=True)
    
    # Company and creator
    company_id = Column(UUID(as_uuid=True), ForeignKey("company.id", ondelete="CASCADE"))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # Invitation details
    invited_email = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default='pending')
    
    # Usage tracking
    used = Column(Boolean, default=False)
    used_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    used_at = Column(DateTime, nullable=True)
    
    # Expiration
    expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="invitations")
    creator = relationship("User", foreign_keys=[created_by])
    user_who_used = relationship("User", foreign_keys=[used_by])