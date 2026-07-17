# app/api/activities.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, func
from typing import List, Optional
import uuid
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.models.location import Location
from app.models.activity import Activity
from app.models.types import Types
from app.models.user import User
from app.schemas.activity import ActivityCreate, ActivityOut
from app.api.deps import get_current_user
from app.api.deps import get_current_company_id
from app.services.enforce_limits import enforce_company_creation_limits

router = APIRouter()

# ---------- Schemas ----------
class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    activity_type: Optional[uuid.UUID] = None
    gallery: Optional[List[dict]] = None
    location_id: Optional[uuid.UUID] = None
    guide_leader: Optional[uuid.UUID] = None 

# ---------- Helper function ----------
def normalize_gallery(gallery):
    """Normaliza gallery si viene como lista de strings"""
    if not gallery:
        return []
    if isinstance(gallery, list):
        result = []
        for i, item in enumerate(gallery):
            if isinstance(item, str):
                result.append({"url": item, "tag": "", "position": i})
            elif isinstance(item, dict):
                result.append({
                    "url": item.get("url", ""),
                    "tag": item.get("tag", ""),
                    "position": item.get("position", i)
                })
        return result
    return []

# ---------- Endpoints ----------

@router.get("/", response_model=List[ActivityOut])
def list_activities(db: Session = Depends(get_db)):
    """
    Listar todas las actividades, incluyendo relaciones: location, type, creator.
    """
    items = (
        db.query(Activity)
        .options(
            selectinload(Activity.location),
            selectinload(Activity.type),  # ✅ Cargar type
            selectinload(Activity.creator),
            selectinload(Activity.leader),
        )
        .all()
    )
    
    for a in items:
        a.gallery = normalize_gallery(a.gallery)
    
    return items


@router.get("/search", response_model=List[ActivityOut])
def search_activities(q: str, db: Session = Depends(get_db)):
    """
    Buscar actividades por título, descripción o tipo.
    """
    query = f"%{q.lower()}%"
    items = (
        db.query(Activity)
        .options(
            selectinload(Activity.location),
            selectinload(Activity.type),  # ✅ Cargar type
            selectinload(Activity.creator),
            selectinload(Activity.leader),
        )
        .join(Types, Activity.activity_type == Types.id)
        .filter(
            or_(
                func.lower(Activity.title).like(query),
                func.lower(Activity.description).like(query),
                func.lower(Types.type_name).like(query)
            )
        )
        .all()
    )
    
    for a in items:
        a.gallery = normalize_gallery(a.gallery)
    
    return items


@router.get("/{activity_id}", response_model=ActivityOut)
def get_activity(activity_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Obtiene una actividad por ID, incluyendo relaciones: location, type, creator.
    """
    activity = (
        db.query(Activity)
        .options(
            selectinload(Activity.location),
            selectinload(Activity.type),  # ✅ Cargar type
            selectinload(Activity.creator),
            selectinload(Activity.leader),
        )
        .filter(Activity.id == activity_id)
        .first()
    )
    
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    activity.gallery = normalize_gallery(activity.gallery)
    return activity


@router.post("/", response_model=ActivityOut, status_code=status.HTTP_201_CREATED)
def create_activity(
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    company_id = Depends(get_current_company_id),
):
    """
    Crea una nueva actividad validando location, type y asignando created_by.
    """
    print(f"Received payload: {payload.dict()}")
    
    # Valida que location_id exista
    location = db.query(Location).filter(Location.id == payload.location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Valida que el activity_type exista
    act_type = db.query(Types).filter(Types.id == payload.activity_type).first()
    if not act_type:
        raise HTTPException(status_code=404, detail="Activity type not found")
    
    # Si se proporciona guide_leader, validar que existe
    guide_leader_id = payload.guide_leader if payload.guide_leader else user.id
    
    if payload.guide_leader:
        leader = db.query(User).filter(User.id == payload.guide_leader).first()
        if not leader:
            raise HTTPException(status_code=404, detail="Guide leader not found")
    
    # Normaliza la galería
    normalized_gallery = normalize_gallery(payload.gallery)
    
    # Crea la actividad
    act = Activity(
        title=payload.title,
        description=payload.description,
        activity_type=payload.activity_type,
        location_id=payload.location_id,
        gallery=normalized_gallery,
        created_by=user.id,
        guide_leader=guide_leader_id
    )
    
    db.add(act)
    db.commit()
    db.refresh(act)

    # Cargar las relaciones explícitamente
    act = (
        db.query(Activity)
        .options(
            selectinload(Activity.location),
            selectinload(Activity.type),  # ✅ Cargar type
            selectinload(Activity.creator),
            selectinload(Activity.leader),
        )
        .filter(Activity.id == act.id)
        .first()
    )
    
    return act

@router.put("/{activity_id}", response_model=ActivityOut)
def update_activity(
    activity_id: uuid.UUID,
    payload: ActivityUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Actualiza una actividad existente.
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if current_user.role != "admin" and activity.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    # Actualiza solo los campos proporcionados
    update_data = payload.dict(exclude_unset=True)
    
    if "activity_type" in update_data and update_data["activity_type"]:
        type_obj = db.query(Types).filter(Types.id == update_data["activity_type"]).first()
        if not type_obj:
            raise HTTPException(status_code=404, detail="Type not found")
    
    if "guide_leader" in update_data and update_data["guide_leader"]:
        leader = db.query(User).filter(User.id == update_data["guide_leader"]).first()
        if not leader:
            raise HTTPException(status_code=404, detail="Guide leader not found")
    
    if "gallery" in update_data:
        update_data["gallery"] = normalize_gallery(update_data["gallery"])
    
    for field, value in update_data.items():
        setattr(activity, field, value)
    
    activity.updated_at = func.now()
    db.commit()
    db.refresh(activity)
    
    # Recargar con relaciones
    activity = (
        db.query(Activity)
        .options(
            selectinload(Activity.location),
            selectinload(Activity.type),  # ✅ Cargar type
            selectinload(Activity.creator),
            selectinload(Activity.leader),
        )
        .filter(Activity.id == activity_id)
        .first()
    )
    
    return activity

@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(
    activity_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Elimina una actividad (solo admin o creador).
    """
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    
    if current_user.role != "admin" and activity.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    
    db.delete(activity)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)