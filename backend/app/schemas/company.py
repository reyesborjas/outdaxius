# app/schemas/company.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from app.schemas.companymember import CompanyMemberOut

class CompanyBase(BaseModel):
    name: str
    description: Optional[str] = None
    legal_representive: str
    legal_representive_text: str
    legal_representive_phone: str
    is_multinational: bool = False
    legal_name: str
    trade_name: str
    incorporation_date: date
    country: str
    currency: str
    address: str
    entity_type: str

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    legal_representive: Optional[str] = None
    legal_representive_text: Optional[str] = None
    legal_representive_phone: Optional[str] = None
    is_multinational: Optional[bool] = None
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    incorporation_date: Optional[date] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    address: Optional[str] = None
    entity_type: Optional[str] = None

class CompanyOut(CompanyBase):
    id: UUID
    createdby: UUID
    createdat: datetime
    updatedat: datetime
    license_tier: str
    is_active: bool
    subscription_expires_at: Optional[datetime] = None
    current_guides_count: Optional[int] = None
    can_add_guides: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)

class CompanyWithMembers(CompanyOut):
    members: List['CompanyMemberOut'] = []
    
    model_config = ConfigDict(from_attributes=True)

class LicenseInfo(BaseModel):
    tier: str
    max_guides: int
    current_guides: int
    can_add_guides: bool
    expires_at: Optional[datetime] = None