# app/api/company.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
from app.models.team import Team, Team
from app.db.session import get_db
from app.models.company import Company
from app.models.companymember import CompanyMember
from app.models.user import User
from app.schemas.company import (
    CompanyCreate, CompanyOut, CompanyUpdate, 
    CompanyWithMembers, LicenseInfo
)
from app.schemas.companymember import CompanyMemberOut
from app.schemas.invitation import (
    InvitationCreate, InvitationOut, InvitationAccept, InvitationListOut
)
from app.api.deps import get_current_user
from app.services.licensing import LicenseManager
from app.services.invitations import InvitationManager
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from pydantic import ConfigDict
from app.api.teams import Team, TeamMember

from datetime import datetime, timezone
from app.schemas.company_limits import CompanyLimitsResponse, LimitsOut, UsageOut, MonthlyUsageOut
from app.services.plan_limits import get_limits_for_tier, normalize_tier
from app.services.company_usage import historical_usage, monthly_usage, month_window_utc

router = APIRouter(prefix="/companies", tags=["companies"])

# ============================================================================
# COMPANY CRUD
# ============================================================================

@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(
    company: CompanyCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new company (admin or guide only)"""
    if current_user.role not in ["admin", "guide"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only guides and admins can create companies"
        )
    
    db_company = Company(**company.dict(), createdby=current_user.id)
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    
    # Add creator as admin member
    member = CompanyMember(
        companyid=db_company.id,
        userid=current_user.id,
        position="Owner",
        is_admin=True,
        is_active=True
    )
    db.add(member)
    db.commit()
    
    return db_company

@router.get("/{company_id}", response_model=CompanyWithMembers)
def get_company(
    company_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get company details with members"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if user has access
    if current_user.role != "admin":
        is_member = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_active == True
        ).first()
        
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this company"
            )
    members = db.query(CompanyMember).filter(
        CompanyMember.companyid == company_id
    ).all()
    
    # Enriquecer con datos del usuario
    enriched_members = []
    for member in members:
        user = db.query(User).filter(User.id == member.userid).first()
        member_dict = {
            "id": member.id,
            "companyid": member.companyid,
            "userid": member.userid,
            "position": member.position,
            "is_admin": member.is_admin,
            "is_active": member.is_active,
            "joinedat": member.joinedat,
            # Datos del usuario
            "user_display_name": user.display_name if user else None,
            "user_email": user.email if user else None,
            "user_full_name": f"{user.first_name or ''} {user.last_name or ''}".strip() if user else None,
            "user_role": user.role if user else None,
        }
        enriched_members.append(member_dict)
    # Get license info
    license_info = LicenseManager.get_company_license_info(db, company_id)
    
    result = CompanyWithMembers.from_orm(db_company)
    result.current_guides_count = license_info['current_guides']
    result.can_add_guides = license_info['can_add_guides']
    
    return result

@router.get("", response_model=List[CompanyOut])
def list_companies(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        return db.query(Company).all()
    memberships = db.query(CompanyMember).filter(
        CompanyMember.userid == current_user.id,
        CompanyMember.is_active == True
    ).all()
    company_ids = [m.companyid for m in memberships]
    return db.query(Company).filter(Company.id.in_(company_ids)).all()

@router.put("/{company_id}", response_model=CompanyOut)
def update_company(
    company_id: UUID, 
    company: CompanyUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update company (admin members only)"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check if user is admin of company
    if current_user.role != "admin":
        is_admin = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_admin == True,
            CompanyMember.is_active == True
        ).first()
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company admins can update"
            )
    
    for key, value in company.dict(exclude_unset=True).items():
        setattr(db_company, key, value)
    
    db.commit()
    db.refresh(db_company)
    return db_company

# ============================================================================
# LICENSING
# ============================================================================

@router.get("/{company_id}/license", response_model=LicenseInfo)
def get_license_info(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get company license information"""
    # Verify access
    if current_user.role != "admin":
        is_member = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_active == True
        ).first()
        
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this company"
            )
    
    try:
        info = LicenseManager.get_company_license_info(db, company_id)
        return LicenseInfo(**info)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# ============================================================================
# INVITATIONS
# ============================================================================

@router.post("/{company_id}/invitations", response_model=InvitationOut)
def create_invitation(
    company_id: UUID,
    invitation: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create guide invitation for company
    
    - Only company admins can create invitations
    - Validates license limits
    - Email is sent to invited guide (TODO)
    """
    
    # Verify admin permission
    if current_user.role != "admin":
        is_admin = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_admin == True,
            CompanyMember.is_active == True
        ).first()
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company admins can invite guides"
            )
    
    # Validate license
    from app.services.licensing import LicenseManager
    try:
        LicenseManager.validate_license(db, company_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(e)
        )
    
    # Create invitation
    try:
        inv = InvitationManager.create_invitation(
            db=db,
            company_id=company_id,
            invited_email=invitation.invited_email,
            created_by=current_user.id,
            expires_in_days=invitation.expires_in_days
        )
        db.commit()
        db.refresh(inv)
        
        # TODO: Send email
        # send_invitation_email(
        #     to=inv.invited_email,
        #     link=f"{FRONTEND_URL}/accept-invitation?code={inv.code}",
        #     company_name=inv.company.name
        # )
        
        return inv
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invitations/accept", response_model=dict)
def accept_invitation(
    data: InvitationAccept,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept company invitation
    
    - User must be logged in as guide
    - Email must match invitation
    - Creates company_members record
    """
    
    try:
        member = InvitationManager.accept_invitation(
            db=db,
            code=data.code,
            user_id=current_user.id
        )
        db.commit()
        db.refresh(member)
        
        return {
            "status": "success",
            "message": "Welcome to the company!",
            "company_id": str(member.companyid),
            "position": member.position
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
@router.get("/{company_id}/invitations", response_model=List[InvitationListOut])
def list_invitations(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List company invitations (admin members only)"""
    
    # Check access
    if current_user.role != "admin":
        is_admin = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_admin == True,
            CompanyMember.is_active == True
        ).first()
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company admins can view invitations"
            )
    
    from app.models.invitation import InvitationCode
    invitations = db.query(InvitationCode).filter(
        InvitationCode.company_id == company_id
    ).order_by(InvitationCode.created_at.desc()).all()
    
    return invitations

@router.post("/invitations/accept", response_model=CompanyMemberOut)
def accept_invitation(
    data: InvitationAccept,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Accept invitation to join company"""
    
    try:
        member = InvitationManager.accept_invitation(
            db=db,
            code=data.code,
            user_id=current_user.id
        )
        db.commit()
        db.refresh(member)
        return member
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================================
# MEMBERS MANAGEMENT
# ============================================================================

@router.get("/{company_id}/members", response_model=List[CompanyMemberOut])
def list_company_members(
    company_id: UUID, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List company members"""
    
    # Check access
    if current_user.role != "admin":
        is_member = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_active == True
        ).first()
        
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this company"
            )
    
    db_members = db.query(CompanyMember).filter(
        CompanyMember.companyid == company_id
    ).all()

    enriched_members = []
    for member in db_members:
        user = db.query(User).filter(User.id == member.userid).first()
        enriched_members.append({
            "id": member.id,
            "companyid": member.companyid,
            "userid": member.userid,
            "position": member.position,
            "is_admin": member.is_admin,
            "is_active": member.is_active,
            "joinedat": member.joinedat,
            "user_display_name": user.display_name if user else None,
            "user_email": user.email if user else None,
            "user_full_name": f"{user.first_name or ''} {user.last_name or ''}".strip() if user else None,
            "user_role": user.role if user else None,
        })
    return enriched_members

@router.delete("/{company_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    company_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove member from company (admin only)"""
    
    # Check if current user is admin
    if current_user.role != "admin":
        is_admin = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_admin == True,
            CompanyMember.is_active == True
        ).first()
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company admins can remove members"
            )
    
    # Prevent removing owner
    company = db.query(Company).filter(Company.id == company_id).first()
    if company.createdby == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove company owner"
        )
    
    # Find and deactivate member
    member = db.query(CompanyMember).filter(
        CompanyMember.companyid == company_id,
        CompanyMember.userid == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    member.is_active = False
    db.commit()
    
    return None

class TeamCreate(BaseModel):
    name: str


from pydantic import BaseModel, Field

class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

class TeamMemberAdd(BaseModel):
    user_id: UUID

class TeamMemberRoleUpdate(BaseModel):
    team_role: str

class TeamOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_by: UUID
    company_id: UUID
    created_at: datetime
    member_count: int = 0
    
    model_config = ConfigDict(from_attributes=True)

class TeamMemberOut(BaseModel):
    id: UUID
    team_id: UUID
    user_id: UUID
    team_role: str
    joined_at: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)



@router.post("/{company_id}/teams", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    company_id: UUID,
    payload: TeamCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new team within a company.
    Only company admins can create teams.
    Creator is automatically added as team admin.
    """
    
    # Verify company exists and user is admin
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Check admin permission
    if current_user.role != "admin":
        is_admin = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_admin == True,
            CompanyMember.is_active == True
        ).first()
        
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only company admins can create teams"
            )
    
    # Create team
    team = Team(
        name=payload.name,
        description=payload.description,
        created_by=current_user.id,
        company_id=company_id
    )
    db.add(team)
    db.flush()
    
    # Add creator as team admin
    team_member = TeamMember(
        team_id=team.id,
        user_id=current_user.id,
        team_role="admin"
    )
    db.add(team_member)
    db.commit()
    db.refresh(team)
    
    # Count members
    member_count = db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
    
    team_out = TeamOut.model_validate(team)
    team_out.member_count = member_count
    
    return team_out


@router.get("/{company_id}/teams", response_model=List[TeamOut])
def list_teams(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all teams in a company"""
    
    # Verify access
    if current_user.role != "admin":
        is_member = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_active == True
        ).first()
        
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this company"
            )
    
    teams = db.query(Team).filter(Team.company_id == company_id).all()
    
    result = []
    for team in teams:
        member_count = db.query(TeamMember).filter(TeamMember.team_id == team.id).count()
        team_out = TeamOut.model_validate(team)
        team_out.member_count = member_count
        result.append(team_out)
    
    return result


@router.get("/{company_id}/teams/{team_id}/members", response_model=List[TeamMemberOut])
def list_team_members(
    company_id: UUID,
    team_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all members of a team"""
    
    # Verify team belongs to company
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.company_id == company_id
    ).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Verify access
    if current_user.role != "admin":
        is_member = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_active == True
        ).first()
        
        if not is_member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this company"
            )
    
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    
    result = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        member_out = TeamMemberOut.model_validate(member)
        if user:
            member_out.user_email = user.email
            member_out.user_name = user.display_name or f"{user.first_name} {user.last_name}".strip()
        result.append(member_out)
    
    return result


@router.post("/{company_id}/teams/{team_id}/members", status_code=status.HTTP_201_CREATED)
def add_team_member(
    company_id: UUID,
    team_id: UUID,
    payload: TeamMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a member to a team.
    User must be a guide in the company.
    Only team admins can add members.
    """
    
    # Verify team belongs to company
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.company_id == company_id
    ).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check if current user is team admin
    if current_user.role != "admin":
        is_team_admin = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.team_role == "admin"
        ).first()
        
        if not is_team_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team admins can add members"
            )
    
    # Verify user is a guide in the company
    company_member = db.query(CompanyMember).filter(
        CompanyMember.companyid == company_id,
        CompanyMember.userid == payload.user_id,
        CompanyMember.is_active == True
    ).first()
    
    if not company_member:
        raise HTTPException(
            status_code=400,
            detail="User must be an active member of the company"
        )
    
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user or user.role != "guide":
        raise HTTPException(
            status_code=400,
            detail="User must have guide role"
        )
    
    # Check if already a member
    existing = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == payload.user_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User is already a team member"
        )
    
    # Add member
    team_member = TeamMember(
        team_id=team_id,
        user_id=payload.user_id,
        team_role="day_guide"
    )
    db.add(team_member)
    db.commit()
    db.refresh(team_member)
    
    return {"status": "success", "member_id": str(team_member.id)}


@router.patch("/{company_id}/teams/{team_id}/members/{member_id}/role")
def update_member_role(
    company_id: UUID,
    team_id: UUID,
    member_id: UUID,
    payload: TeamMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a team member's role. Only team admins can update roles."""
    
    ALLOWED_ROLES = {"admin", "lead_guide", "expert_guide", "assistant_guide", "day_guide"}
    
    if payload.team_role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(ALLOWED_ROLES)}"
        )
    
    # Verify team belongs to company
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.company_id == company_id
    ).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check if current user is team admin
    if current_user.role != "admin":
        is_team_admin = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.team_role == "admin"
        ).first()
        
        if not is_team_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team admins can update roles"
            )
    
    # Find member
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.team_id == team_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    member.team_role = payload.team_role
    db.commit()
    
    return {"status": "success", "user_id": str(member.user_id), "new_role": payload.team_role}


@router.delete("/{company_id}/teams/{team_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    company_id: UUID,
    team_id: UUID,
    member_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a member from a team. Only team admins can remove members."""
    
    # Verify team belongs to company
    team = db.query(Team).filter(
        Team.id == team_id,
        Team.company_id == company_id
    ).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check if current user is team admin
    if current_user.role != "admin":
        is_team_admin = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.user_id == current_user.id,
            TeamMember.team_role == "admin"
        ).first()
        
        if not is_team_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only team admins can remove members"
            )
    
    # Find member
    member = db.query(TeamMember).filter(
        TeamMember.id == member_id,
        TeamMember.team_id == team_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    # Prevent removing the last admin
    if member.team_role == "admin":
        admin_count = db.query(TeamMember).filter(
            TeamMember.team_id == team_id,
            TeamMember.team_role == "admin"
        ).count()
        
        if admin_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last admin from the team"
            )
    
    db.delete(member)
    db.commit()
    
    return None

@router.get("/{company_id}/teams", response_model=List[dict])
def list_teams_for_company(company_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    teams = db.query(Team).filter_by(company_id=company_id).all()
    return [{"id": str(team.id), "name": team.name, "company_id": str(team.company_id)} for team in teams]

@router.get("/{company_id}/limits", response_model=CompanyLimitsResponse)
def get_company_limits_and_usage(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # reuse your existing access checks pattern:
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(404, detail="Company not found")

    if current_user.role != "admin":
        is_member = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_active == True
        ).first()
        if not is_member:
            raise HTTPException(403, detail="Not a member of this company")

    tier = normalize_tier(db_company.license_tier)
    tier_limits = get_limits_for_tier(db_company.license_tier)

    hist = historical_usage(db, company_id)
    start, end = month_window_utc(datetime.now(timezone.utc))
    mon = monthly_usage(db, company_id, start, end)

    return CompanyLimitsResponse(
        company_id=company_id,
        tier=tier,
        as_of=datetime.now(timezone.utc),
        limits=LimitsOut(
            guides_max=db_company.max_guides,
            max_activities=tier_limits.max_activities,
            max_programs=tier_limits.max_programs,
            max_schedules_total=tier_limits.max_schedules_total,
            max_monthly_bookings=tier_limits.max_monthly_bookings,
            max_monthly_participants=tier_limits.max_monthly_participants,
        ),
        usage_historical=UsageOut(**hist),
        usage_current_month=MonthlyUsageOut(
            from_date=start, to_date=end, bookings=mon["bookings"], participants=mon["participants"]
        ),
    )
