# app/schemas/assignment.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal
from uuid import UUID
from datetime import datetime


class AssignmentProposeCreate(BaseModel):
    activity_schedule_id: UUID
    user_id: UUID
    is_leader: bool = False


class AssignmentSelfAssignCreate(BaseModel):
    activity_schedule_id: UUID
    is_leader: bool = False


class AssignmentDecision(BaseModel):
    decision: Literal["accept", "decline"]
    decline_reason: Optional[str] = None


class AssignmentOut(BaseModel):
    id: UUID
    activity_schedule_id: UUID
    user_id: UUID
    home_team_id: UUID
    home_company_id: UUID
    is_leader: bool
    status: str
    proposed_by: UUID
    proposed_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    decline_reason: Optional[str] = None

    # Denormalized display fields, populated by the router.
    user_display_name: Optional[str] = None
    activity_title: Optional[str] = None
    schedule_start: Optional[datetime] = None
    schedule_end: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AssignmentsMineOut(BaseModel):
    incoming: list[AssignmentOut]
    mine: list[AssignmentOut]
