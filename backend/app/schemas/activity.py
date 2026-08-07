# backend/app/schemas/activity.py
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.types import TypesOut

from app.schemas.location import LocationOut, LocationResolveIn
from app.schemas.user import UserPublicOut

class ActivityBase(BaseModel):
    title: str
    description: Optional[str] = None
    activity_type: UUID
    type: TypesOut

class ActivityCreate(BaseModel):
    title: str
    description: Optional[str] = None
    activity_type: UUID
    location_id: UUID
    guide_leader: Optional[UUID] = None  # 🔥 NUEVO
    gallery: Optional[List[Dict]] = Field(default_factory=list)
    is_shared: bool = False

class ActivityOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    activity_type: UUID
    type: Optional[TypesOut] = None
    location: Optional[LocationOut] = None
    gallery: List[Dict] = Field(default_factory=list)
    # UserPublicOut, never UserOut: this endpoint is unauthenticated (see UserPublicOut).
    creator: Optional[UserPublicOut] = None
    leader: Optional[UserPublicOut] = None
    guide_leader: Optional[UUID] = None
    team_id: Optional[UUID] = None
    company_id: Optional[UUID] = None
    is_shared: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
