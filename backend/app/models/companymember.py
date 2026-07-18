# app/models/companymember.py

import uuid
from sqlalchemy import Column, ForeignKey, String, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from sqlalchemy.orm import relationship, synonym

class CompanyMember(Base):
    __tablename__ = "company_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    companyid = Column(UUID(as_uuid=True), ForeignKey("company.id"), nullable=False)
    userid = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    position = Column(String, nullable=False)
    is_admin = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    joinedat = Column(Date, nullable=True)
    # The DB column is "joinedat" (no underscore); every Pydantic schema field and frontend
    # payload key is "joined_at". Without this alias, CompanyMemberOut's from_attributes lookup
    # silently misses and serializes null on every row.
    joined_at = synonym("joinedat")

    company = relationship("Company", back_populates="members")
    user = relationship("User")