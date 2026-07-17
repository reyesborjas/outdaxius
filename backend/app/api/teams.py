# app/api/teams.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.team import Team, TeamMember
from app.models.companymember import CompanyMember
from app.models.user import User

router = APIRouter(prefix="/teams", tags=["teams"])

# Esquema para inputs
from pydantic import BaseModel

class TeamCreate(BaseModel):
    name: str
    description: str = ""

class TeamMemberAssign(BaseModel):
    userid: UUID

# Crear equipo y adicionar admin actual (company.createdby) como team member
@router.post("/", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_team(company_id: UUID, payload: TeamCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Validar que el usuario sea admin en la empresa
    company_member = db.query(CompanyMember).filter(
        CompanyMember.companyid == company_id,
        CompanyMember.userid == current_user.id,
        CompanyMember.isadmin == True,
        CompanyMember.isactive == True
    ).first()
    if not company_member:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 2. Crear el equipo
    team = Team(
        name=payload.name,
        description=payload.description,
        createdby=current_user.id,
        companyid=company_id
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    # 3. Insertar al admin como miembro del equipo (TeamMember)
    team_member = TeamMember(
        teamid=team.id,
        userid=current_user.id
        # Otros campos por defecto (joinedat, etc.)
    )
    db.add(team_member)
    db.commit()
    db.refresh(team_member)

    return {"id": str(team.id), "admin_member_id": str(team_member.id)}

# Endpoint para añadir miembros al equipo solo si pertenecen a company_members
@router.post("/{team_id}/members", response_model=dict)
def add_team_member(team_id: UUID, assignment: TeamMemberAssign, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # 1. Validar que el usuario autenticado es admin en la empresa del equipo
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    company_member = db.query(CompanyMember).filter(
        CompanyMember.companyid == team.companyid,
        CompanyMember.userid == current_user.id,
        CompanyMember.isadmin == True,
        CompanyMember.isactive == True
    ).first()
    if not company_member:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 2. Validar que el usuario a añadir está en company_members
    cmember = db.query(CompanyMember).filter(
        CompanyMember.companyid == team.companyid,
        CompanyMember.userid == assignment.userid,
        CompanyMember.isactive == True
    ).first()
    if not cmember:
        raise HTTPException(status_code=400, detail="User is not a member of company")

    # 3. Evitar duplicados en el mismo equipo
    existing = db.query(TeamMember).filter(
        TeamMember.teamid == team.id,
        TeamMember.userid == assignment.userid
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already in team")

    # 4. Asignar a team
    team_member = TeamMember(
        teamid=team.id,
        userid=assignment.userid
        # joinedat y otros campos por defecto
    )
    db.add(team_member)
    db.commit()
    db.refresh(team_member)

    return {"added_member_id": str(team_member.id)}

class TeamMemberRoleUpdate(BaseModel):
    team_role: str  # Validar valores en endpoint

@router.put("/{team_id}/members/{user_id}/role", status_code=200)
def update_team_member_role(
    team_id: UUID,
    user_id: UUID,
    payload: TeamMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validar que current_user tiene rol admin en este equipo
    admin_membership = db.query(TeamMember).filter_by(
        team_id=team_id, user_id=current_user.id, team_role='admin'
    ).first()
    if not admin_membership:
        raise HTTPException(403, "Solo admin puede modificar roles")
    # Validar valor de team_role
    ALLOWED_ROLES = {"admin","lead_guide","expert_guide","assistant_guide","day_guide"}
    if payload.team_role not in ALLOWED_ROLES:
        raise HTTPException(400, f"Rol no permitido: {payload.team_role}")
    # Actualizar rol
    member = db.query(TeamMember).filter_by(team_id=team_id, user_id=user_id).first()
    if not member:
        raise HTTPException(404, "Miembro no existe")
    member.team_role = payload.team_role
    db.commit()
    return {"status": "ok", "user_id": str(user_id), "new_role": payload.team_role}