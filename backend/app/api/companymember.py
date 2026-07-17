# app/api/companymember.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.models.companymember import CompanyMember
from app.schemas.companymember import CompanyMemberCreate, CompanyMemberOut, CompanyMemberBase

router = APIRouter(prefix="/companymembers", tags=["companymembers"])

# POST /companymembers
@router.post("/", response_model=CompanyMemberOut, status_code=status.HTTP_201_CREATED)
def create_company_member(member: CompanyMemberCreate, db: Session = Depends(get_db)):
    db_member = CompanyMember(**member.dict())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

# GET /companymembers/{id}
@router.get("/{id}", response_model=CompanyMemberOut)
def get_company_member(id: UUID, db: Session = Depends(get_db)):
    db_member = db.query(CompanyMember).filter(CompanyMember.id == id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Company member not found")
    return db_member

# GET /companymembers
@router.get("/", response_model=List[CompanyMemberOut])
def list_company_members(db: Session = Depends(get_db)):
    return db.query(CompanyMember).all()

# PUT /companymembers/{id}
@router.put("/{id}", response_model=CompanyMemberOut)
def update_company_member(id: UUID, member: CompanyMemberBase, db: Session = Depends(get_db)):
    db_member = db.query(CompanyMember).filter(CompanyMember.id == id).first()
    if not db_member:
        raise HTTPException(status_code=404, detail="Company member not found")
    for key, value in member.dict(exclude_unset=True).items():
        setattr(db_member, key, value)
    db.commit()
    db.refresh(db_member)
    return db_member
