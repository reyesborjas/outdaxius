# app/api/companymember.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.companymember import CompanyMember
from app.models.user import User
from app.schemas.companymember import CompanyMemberCreate, CompanyMemberOut, CompanyMemberBase
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/companymembers", tags=["companymembers"])


def _require_company_admin(db: Session, current_user: User, company_id: UUID) -> None:
    """Commercial authority check: platform admin, or an active is_admin member of this company."""
    if current_user.role == "admin":
        return
    is_admin = db.query(CompanyMember).filter(
        CompanyMember.companyid == company_id,
        CompanyMember.userid == current_user.id,
        CompanyMember.is_admin == True,
        CompanyMember.is_active == True,
    ).first()
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company admin access required")


def _require_company_member(db: Session, current_user: User, company_id: UUID) -> None:
    if current_user.role == "admin":
        return
    is_member = db.query(CompanyMember).filter(
        CompanyMember.companyid == company_id,
        CompanyMember.userid == current_user.id,
        CompanyMember.is_active == True,
    ).first()
    if not is_member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this company")


# POST /companymembers
@router.post("/", response_model=CompanyMemberOut, status_code=status.HTTP_201_CREATED)
def create_company_member(
    member: CompanyMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_company_admin(db, current_user, member.companyid)
    db_member = CompanyMember(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

# GET /companymembers/{id}
@router.get("/{id}", response_model=CompanyMemberOut)
def get_company_member(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_member = db.query(CompanyMember).filter(CompanyMember.id == id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Company member not found")
    _require_company_member(db, current_user, db_member.companyid)
    return db_member

# GET /companymembers
# NOTE: unscoped by company (would leak cross-tenant membership data to a company admin),
# so this is platform-admin-only for now. Revisit alongside the joinedat/joined_at fix in
# Phase 3 — company.py already exposes a properly company-scoped equivalent.
@router.get("/", response_model=List[CompanyMemberOut])
def list_company_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return db.query(CompanyMember).all()

# PUT /companymembers/{id}
@router.put("/{id}", response_model=CompanyMemberOut)
def update_company_member(
    id: UUID,
    member: CompanyMemberBase,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_member = db.query(CompanyMember).filter(CompanyMember.id == id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Company member not found")
    _require_company_admin(db, current_user, db_member.companyid)
    for key, value in member.dict(exclude_unset=True).items():
        setattr(db_member, key, value)
    db.commit()
    db.refresh(db_member)
    return db_member
