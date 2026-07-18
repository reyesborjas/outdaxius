# app/api/pograms.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, func
from typing import List, Optional
import uuid
from uuid import UUID
from app.db.session import get_db
from app.models.programs import Program
from app.models.types import Types
from app.models.user import User
from app.schemas.program import ProgramCreate, ProgramOut
from app.api.deps import get_current_user
from pydantic import BaseModel
from app.schemas.activity import ActivityOut
from app.models.activity import Activity
from app.models.programactivity import ProgramActivity
from app.api.deps import get_current_company_id
from app.services.enforce_limits import enforce_company_creation_limits
from app.core.permissions import require_action, check_permission, get_user_team_membership


router = APIRouter()

# ---------- Schemas ----------
class ProgramUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    program_type: Optional[uuid.UUID] = None
    gallery: Optional[List[dict]] = None
    min_activities: Optional[int] = None
    guide_leader: Optional[uuid.UUID] = None
    # agregar otros campos relevantes

# ---------- Endpoints ----------
@router.get("", response_model=List[ProgramOut])
@router.get("/", response_model=List[ProgramOut])
def list_programs(db: Session = Depends(get_db)):
    items = (
        db.query(Program)
        .options(
            selectinload(Program.creator),
            selectinload(Program.type)  # cargar el type vinculado
        )
        .all()
    )

    # Normaliza gallery si viene como ["url1","url2",...]
    for p in items:
        g = p.gallery
        if isinstance(g, list) and (len(g) == 0 or (len(g) > 0 and isinstance(g[0], str))):
            p.gallery = [{"url": u, "tag": "", "position": i} for i, u in enumerate(g or [])]
    return items

@router.post("/", response_model=ProgramOut, status_code=status.HTTP_201_CREATED)
def create_program(
    payload: ProgramCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_action("program.create")),
    company_id = Depends(get_current_company_id)
):
    if company_id:
        enforce_company_creation_limits(db, company_id, metric="programs")
    type_obj = db.query(Types).filter(Types.id == payload.program_type).first()
    if not type_obj:
        raise HTTPException(status_code=404, detail="Type not found")

    # 🔥 NUEVO: Si se proporciona guide_leader, validar que existe
    guide_leader_id = payload.guide_leader if payload.guide_leader else user.id

    if payload.guide_leader:
        leader = db.query(User).filter(User.id == payload.guide_leader).first()
        if not leader:
            raise HTTPException(status_code=404, detail="Guide leader not found")

    # require_action already confirmed the caller has role_level 1 in some team, so this is
    # always resolvable here.
    membership = get_user_team_membership(db, user.id)

    prog = Program(
        title=payload.title,
        description=payload.description,
        program_type=payload.program_type,
        created_by=user.id,
        guide_leader=guide_leader_id,  # 🔥 NUEVO
        gallery=payload.gallery or [],
        team_id=membership.team_id,
    )
    db.add(prog)
    db.commit()
    db.refresh(prog)
    db.refresh(prog, ['creator', 'type', 'leader'])
    return prog

@router.put("/{program_id}", response_model=ProgramOut)
def update_program(
    program_id: uuid.UUID,
    payload: ProgramUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    if not check_permission(db, current_user, "program.edit", team_id=program.team_id):
        raise HTTPException(status_code=403, detail="Not allowed")

    update_data = payload.dict(exclude_unset=True)
    
    if "program_type" in update_data and update_data["program_type"]:
        type_obj = db.query(Types).filter(Types.id == update_data["program_type"]).first()
        if not type_obj:
            raise HTTPException(status_code=404, detail="Type not found")
    
    # 🔥 NUEVO: Validar guide_leader si se proporciona
    if "guide_leader" in update_data and update_data["guide_leader"]:
        leader = db.query(User).filter(User.id == update_data["guide_leader"]).first()
        if not leader:
            raise HTTPException(status_code=404, detail="Guide leader not found")
    
    for field, value in update_data.items():
        setattr(program, field, value)
    
    program.updated_at = func.now()
    db.commit()
    db.refresh(program, ['creator', 'type', 'leader'])  # 🔥 NUEVO: agregar 'leader'
    return program

@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_program(
    program_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    p = db.query(Program).filter(Program.id == program_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Program not found")
    if not check_permission(db, current_user, "program.delete", team_id=p.team_id):
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(p)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/search", response_model=List[ProgramOut])
def search_programs(q: str, db: Session = Depends(get_db)):
    q = (q or "").strip().lower()
    if not q:
        return []
    like = f"%{q}%"
    return (
        db.query(Program)
        .outerjoin(Types, Program.program_type == Types.id)
        .filter(
            or_(
                func.lower(Program.title).like(like),
                func.lower(Types.type_name).like(like),
            )
        )
        .all()
    )
@router.get("/{program_id}/activities", response_model=list[ActivityOut])
def get_program_activities(program_id: UUID, db: Session = Depends(get_db)):
    program = db.query(Program).options(selectinload(Program.activities)).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return program.activities

@router.post("/{program_id}/activities", status_code=status.HTTP_201_CREATED)
def link_activities_to_program(
    program_id: UUID,
    activity_ids: List[UUID],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Vincular múltiples actividades a un programa
    """
    # Verificar que el programa existe
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Verificar permisos
    if not check_permission(db, current_user, "program.edit", team_id=program.team_id):
        raise HTTPException(status_code=403, detail="Not allowed to modify this program")
    
    # Verificar que todas las actividades existen
    activities = db.query(Activity).filter(Activity.id.in_(activity_ids)).all()
    found_ids = {a.id for a in activities}
    missing_ids = set(activity_ids) - found_ids
    
    if missing_ids:
        raise HTTPException(
            status_code=404, 
            detail=f"Activities not found: {', '.join(str(id) for id in missing_ids)}"
        )
    
    # Crear vínculos (evitando duplicados)
    created_count = 0
    for activity_id in activity_ids:
        # Verificar si ya existe el vínculo
        existing = db.query(ProgramActivity).filter(
            ProgramActivity.program_id == program_id,
            ProgramActivity.activity_id == activity_id
        ).first()
        
        if not existing:
            link = ProgramActivity(
                program_id=program_id,
                activity_id=activity_id
            )
            db.add(link)
            created_count += 1
    
    db.commit()
    
    return {
        "status": "ok",
        "program_id": str(program_id),
        "linked_count": created_count,
        "total_activities": len(activity_ids)
    }

# 🔥 NUEVO: Desvincular una actividad de un programa
@router.delete("/{program_id}/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_activity_from_program(
    program_id: UUID,
    activity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Desvincular una actividad de un programa
    """
    # Verificar que el programa existe
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Verificar permisos
    if not check_permission(db, current_user, "program.edit", team_id=program.team_id):
        raise HTTPException(status_code=403, detail="Not allowed to modify this program")
    
    # Buscar y eliminar el vínculo
    link = db.query(ProgramActivity).filter(
        ProgramActivity.program_id == program_id,
        ProgramActivity.activity_id == activity_id
    ).first()
    
    if not link:
        raise HTTPException(
            status_code=404, 
            detail=f"Activity {activity_id} is not linked to program {program_id}"
        )
    
    db.delete(link)
    db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)