# app/models/company.py
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Date, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Company(Base):
    __tablename__ = "company"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text)
    createdby = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    createdat = Column(DateTime, server_default=func.now())
    updatedat = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Legal information -- nullable because an auto-created personal company (every guide gets
    # one, see app.services.personal_team) has no real business registration to supply. Only
    # actually-registered companies (created via POST /companies) are expected to fill these in.
    legal_representive = Column(Text, nullable=True)
    legal_representive_text = Column(Text, nullable=True)
    legal_representive_phone = Column(Text, nullable=True)
    is_multinational = Column(Boolean, nullable=False, default=False)
    legal_name = Column(Text, nullable=True)
    trade_name = Column(Text, nullable=True)
    incorporation_date = Column(Date, nullable=True)
    country = Column(Text, nullable=True)
    currency = Column(Text, nullable=True)
    address = Column(Text, nullable=True)
    entity_type = Column(Text, nullable=True)
    
    # Licensing fields. max_guides was dropped by the Phase 2 migration (spec 2.9: "limits move
    # to plan_limits configuration, not a database column") -- see app.services.licensing for the
    # tier-based replacement.
    license_tier = Column(String(20), nullable=False, default='free')
    is_active = Column(Boolean, nullable=False, default=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[createdby])
    members = relationship("CompanyMember", back_populates="company", cascade="all, delete-orphan")
    invitations = relationship("InvitationCode", back_populates="company", cascade="all, delete-orphan")