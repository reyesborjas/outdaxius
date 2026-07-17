# backend/app/schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional, Any, Dict
from pydantic import BaseModel, ConfigDict
from datetime import date
import uuid


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    national_id: Optional[str] = None
    passport_number: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    preferred_language: Optional[str] = None
    birth_date: Optional[date] = None
    tax_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    fiscal_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AdminUserUpdate(BaseModel):
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    national_id: Optional[str] = None
    passport_number: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    preferred_language: Optional[str] = None
    birth_date: Optional[date] = None
    tax_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    fiscal_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class UserOut(BaseModel):
    id: uuid.UUID
    display_name: str
    email: EmailStr
    role: str
    preferred_language: Optional[str] = None
    is_active: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    national_id: Optional[str] = None
    passport_number: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    birth_date: Optional[date] = None
    tax_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    fiscal_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class UserWithCompanyOut(UserOut):
    """Extended user response with company information for guides"""
    company_name: Optional[str] = None
    company_id: Optional[uuid.UUID] = None
    is_company_admin: Optional[bool] = None
    company_position: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True, extra="allow")

class UserCreate(BaseModel):
    # required
    display_name: str
    email: EmailStr
    password: str
    role: str

    # optional
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    national_id: Optional[str] = None
    passport_number: Optional[str] = None
    phone: Optional[str] = None
    profile_picture: Optional[str] = None
    preferred_language: Optional[str] = None
    birth_date: Optional[date] = None
    tax_id: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    fiscal_data: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = True

