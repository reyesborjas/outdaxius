# app/schemas/company.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date
from app.schemas.companymember import CompanyMemberOut

class CompanyCreate(BaseModel):
    # A real, actually-registered business, created via the manual "Create Company" flow --
    # these stay required. Auto-created personal companies (see app.services.personal_team) are
    # built directly as ORM objects, not through this schema, so this validation is unaffected.
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

class CompanyOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    createdby: UUID
    createdat: datetime
    updatedat: datetime
    # Optional here (unlike CompanyCreate): an auto-created personal company never fills these in.
    legal_representive: Optional[str] = None
    legal_representive_text: Optional[str] = None
    legal_representive_phone: Optional[str] = None
    is_multinational: bool = False
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    incorporation_date: Optional[date] = None
    country: Optional[str] = None
    currency: Optional[str] = None
    address: Optional[str] = None
    entity_type: Optional[str] = None
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

class CancellationRateOut(BaseModel):
    cancellation_rate: Optional[float] = None
    vendor_cancellations: int
    total_bookings: int
    window_days: int
    sufficient_data: bool

class PublicCompanyOut(BaseModel):
    """The public storefront view -- deliberately excludes legal/contact fields (address,
    legal_representive*, tax info) that CompanyOut exposes to authenticated members."""
    id: UUID
    name: str
    description: Optional[str] = None
    trade_name: Optional[str] = None
    country: Optional[str] = None
    cancellation: CancellationRateOut

    model_config = ConfigDict(from_attributes=True)
