# app/schemas/membership_request.py
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime


class MembershipInviteCreate(BaseModel):
    team_id: UUID
    target_user_id: Optional[UUID] = None
    target_email: Optional[EmailStr] = None
    offered_level: int = Field(default=4, ge=1, le=4)
    message: Optional[str] = None
    # Set when a company officer proposes one of their OWN company's guides for a different team.
    on_behalf_of_company_id: Optional[UUID] = None


class MembershipApplyCreate(BaseModel):
    team_id: UUID
    message: Optional[str] = None


class ConsentDecision(BaseModel):
    decision: Literal["granted", "refused"]


class MembershipRequestOut(BaseModel):
    id: UUID
    direction: str
    team_id: UUID
    company_id: UUID
    target_user_id: Optional[UUID] = None
    target_email: Optional[str] = None
    offered_level: int
    created_by: UUID
    on_behalf_of_company_id: Optional[UUID] = None
    target_consent: str
    message: Optional[str] = None
    status: str
    expires_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Denormalized display fields, populated by the router for a UI that shouldn't have to
    # make N follow-up requests just to render a list of pending requests.
    team_name: Optional[str] = None
    company_name: Optional[str] = None
    target_display_name: Optional[str] = None
    created_by_display_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MembershipRequestsMineOut(BaseModel):
    incoming: list[MembershipRequestOut]
    outgoing: list[MembershipRequestOut]
    team_pending: list[MembershipRequestOut]


class DepartureStatusOut(BaseModel):
    can_leave: bool
    reason: Optional[str] = None
