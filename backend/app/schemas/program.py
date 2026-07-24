# backend/app/schemas/programs.py
from pydantic import BaseModel
from uuid import UUID
import uuid
from app.schemas.types import TypesOut
from app.schemas.user import UserOut
from typing import Optional, List

class ProgramOut(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    gallery: Optional[List[dict]] = None
    min_activities: Optional[int] = None
    program_type: UUID
    type: TypesOut
    is_shared: bool = False
    creator: Optional[UserOut] = None
    team_id: Optional[UUID] = None
    company_id: Optional[UUID] = None

    class Config:
        from_attributes = True

class ProgramCreate(BaseModel):
    title: str
    description: Optional[str]
    gallery: Optional[List[dict]]
    min_activities: Optional[int]
    program_type: UUID
    guide_leader: Optional[UUID] = None
    is_shared: bool = False
