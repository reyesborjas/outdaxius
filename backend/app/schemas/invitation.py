# app/schemas/invitation.py
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class InvitationCreate(BaseModel):
    invited_email: EmailStr
    expires_in_days: int = Field(default=7, ge=1, le=30)
    
    @field_validator('invited_email')
    @classmethod
    def email_must_be_lowercase(cls, v):
        return v.lower()

class InvitationOut(BaseModel):
    id: UUID
    code: str
    company_id: UUID
    invited_email: Optional[str] = None
    status: str
    used: bool
    expires_at: datetime
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InvitationAccept(BaseModel):
    code: str

class InvitationListOut(BaseModel):
    id: UUID
    invited_email: Optional[str] = None
    status: str
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)