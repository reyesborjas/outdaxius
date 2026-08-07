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

class UserPublicOut(BaseModel):
    """
    The safe subset of a user to embed in catalogue responses (activities, programs).

    UserOut must never be used there. GET /activities/ and GET /programs/ take no authentication
    at all, so anything embedded in them is world-readable -- and UserOut carries email,
    national_id, passport_number, phone, birth_date, tax_id and the whole fiscal_data blob
    (legal representative, tax address, and the rest). That let an unauthenticated caller
    enumerate every company's catalogue and harvest its guides' personal and tax data.

    GET /users/{id} is properly locked down (authenticated, admin-or-self), so the embedded
    creator/leader object was the only route to that data.

    What stays here is what a listing legitimately renders: who to credit for the activity, and
    an avatar. Nothing that identifies the person off-platform.
    """
    id: uuid.UUID
    display_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str
    profile_picture: Optional[str] = None

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

