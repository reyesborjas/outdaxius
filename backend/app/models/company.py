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
    
    # Legal information
    legal_representive = Column(Text, nullable=False)
    legal_representive_text = Column(Text, nullable=False)
    legal_representive_phone = Column(Text, nullable=False)
    is_multinational = Column(Boolean, nullable=False, default=False)
    legal_name = Column(Text, nullable=False)
    trade_name = Column(Text, nullable=False)
    incorporation_date = Column(Date, nullable=False)
    country = Column(Text, nullable=False)
    currency = Column(Text, nullable=False)
    address = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)
    
    # 🔥 NEW: Licensing fields
    license_tier = Column(String(20), nullable=False, default='free')
    max_guides = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    subscription_expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[createdby])
    members = relationship("CompanyMember", back_populates="company", cascade="all, delete-orphan")
    invitations = relationship("InvitationCode", back_populates="company", cascade="all, delete-orphan")