# app/schemas/companymember.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import date

class CompanyMemberBase(BaseModel):
    position: str
    is_admin: bool = False
    is_active: bool = True
    joined_at: Optional[date] = None

class CompanyMemberCreate(CompanyMemberBase):
    companyid: UUID
    userid: UUID

class CompanyMemberOut(CompanyMemberBase):
    id: UUID
    companyid: UUID
    userid: UUID
    # 🔥 NUEVO: Campos adicionales del usuario
    user_display_name: Optional[str] = None
    user_email: Optional[str] = None
    user_full_name: Optional[str] = None
    user_role: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)