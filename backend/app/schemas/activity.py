# backend/app/schemas/activity.py
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.types import TypesOut

from app.schemas.location import LocationOut, LocationResolveIn
from app.schemas.user import UserOut  # quita esta línea si tu respuesta no expone "creator"

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

class ActivityOut(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    activity_type: UUID
    type: Optional[TypesOut] = None
    location: Optional[LocationOut] = None
    gallery: List[Dict] = Field(default_factory=list)
    creator: Optional[UserOut] = None
    leader: Optional[UserOut] = None  
    guide_leader: Optional[UUID] = None  
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
