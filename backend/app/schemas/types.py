from pydantic import BaseModel
from uuid import UUID

class TypesOut(BaseModel):
    id: UUID
    type_name: str
    experience_type: str

    class Config:
        from_attributes = True  # Para compatibilidad con SQLAlchemy Objects
