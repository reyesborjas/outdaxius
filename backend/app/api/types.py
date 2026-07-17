from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.types import Types
from app.schemas.types import TypesOut
from uuid import UUID
from typing import Optional
from fastapi import Query

router = APIRouter()

@router.get("/", response_model=list[TypesOut])
def list_types(
    db: Session = Depends(get_db),
    experience_type: Optional[str] = Query(None, description="Filter by experience_type: 'activity', 'program', or 'both'")
):
    """
    Lista todos los tipos disponibles.
    Filtra por experience_type si se proporciona.
    """
    query = db.query(Types)
    
    if experience_type:
        # Si pide 'activity', traer los que son 'activity' o 'both'
        if experience_type.lower() == "activity":
            query = query.filter(Types.experience_type.in_(["activity", "both"]))
        # Si pide 'program', traer los que son 'program' o 'both'
        elif experience_type.lower() == "program":
            query = query.filter(Types.experience_type.in_(["program", "both"]))
        # Si pide 'both', traer solo los marcados como 'both'
        elif experience_type.lower() == "both":
            query = query.filter(Types.experience_type == "both")
    
    return query.order_by(Types.type_name).all()
   

@router.get("/{type_id}", response_model=TypesOut)
def get_type(type_id: UUID, db: Session = Depends(get_db)):
    """Obtiene un tipo específico por ID"""
    type_obj = db.query(Types).filter(Types.id == type_id).first()
    if not type_obj:
        raise HTTPException(status_code=404, detail="Type not found")
    return type_obj

@router.post("/", response_model=TypesOut)
def create_type(type_in: TypesOut, db: Session = Depends(get_db)):
    type_obj = Types(**type_in.dict())
    db.add(type_obj)
    db.commit()
    db.refresh(type_obj)
    return type_obj
