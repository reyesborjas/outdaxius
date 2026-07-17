# app/api/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List, Optional, Union
from uuid import UUID
from pydantic import ConfigDict
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserUpdate, UserOut, UserWithCompanyOut, UserCreate
from app.api.deps import get_current_user
from app.schemas.user import UserCreate
from app.api.deps import require_admin


router = APIRouter()

@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    """
    Permite al usuario autenticado actualizar solo sus propios datos.
    Solo se actualizan los campos enviados (exclude_unset=True).
    """
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(user, attr, value)
    db.commit()
    db.refresh(user)
    return user

@router.get("/", response_model=List[Union[UserOut, UserWithCompanyOut]])
def list_users(
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lista usuarios. Si role=guide, enriquece con información de company.
    """
    if current_user.role not in {"admin", "company", "guide"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Insufficient permissions"
        )
    
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.all()
    
    # ✅ Si se solicitan guides, enriquecer con info de company
    if role == "guide":
        from app.models.companymember import CompanyMember
        from app.models.company import Company
        
        enriched_users = []
        for user in users:
            # Convertir a dict base
            user_dict = {
                "id": user.id,
                "display_name": user.display_name,
                "email": user.email,
                "role": user.role,
                "preferred_language": user.preferred_language,
                "is_active": user.is_active,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "national_id": user.national_id,
                "passport_number": user.passport_number,
                "phone": user.phone,
                "profile_picture": user.profile_picture,
                "birth_date": user.birth_date,
                "tax_id": user.tax_id,
                "profile": user.profile,
                "fiscal_data": user.fiscal_data,
            }
            
            # Buscar membership activo
            membership = db.query(CompanyMember).filter(
                CompanyMember.userid == user.id,
                CompanyMember.is_active == True
            ).first()
            
            if membership:
                company = db.query(Company).filter(
                    Company.id == membership.companyid
                ).first()
                
                if company:
                    user_dict["company_name"] = company.name
                    user_dict["company_id"] = company.id
                    user_dict["is_company_admin"] = membership.is_admin
                    user_dict["company_position"] = membership.position
            
            enriched_users.append(user_dict)
        
        return enriched_users
    
    # Para roles que no son guide, retornar sin enriquecimiento
    return users

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/me/company-info", response_model=dict)
def get_my_company_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene información de empresa del guía:
    - Si es miembro de una company formal: retorna datos de company table
    - Si es independiente: retorna datos de user.fiscal_data
    """
    if current_user.role != "guide":
        raise HTTPException(
            status_code=403, 
            detail="Only guides can access company info"
        )
    
    from app.models.companymember import CompanyMember
    from app.models.company import Company
    
    # Verificar si es miembro de una empresa formal
    membership = db.query(CompanyMember).filter(
        CompanyMember.userid == current_user.id,
        CompanyMember.is_active == True
    ).first()
    
    if membership:
        # Guía asociado a empresa
        company = db.query(Company).filter(
            Company.id == membership.companyid
        ).first()
        return {
            "type": "company_member",
            "company_id": str(company.id),
            "company_name": company.name,
            "is_admin": membership.is_admin,
            "position": membership.position,
            "data": {
                "legal_name": company.legal_name,
                "trade_name": company.trade_name,
                "country": company.country,
                "address": company.address,
            }
        }
    else:
        # Guía independiente
        return {
            "type": "independent",
            "company_id": None,
            "company_name": None,
            "data": current_user.fiscal_data or {}
        }


@router.get("/{userid}", response_model=UserOut)
def get_user_by_id(userid: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user = db.query(User).filter(User.id == userid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != "admin" and current_user.id != userid:
        raise HTTPException(status_code=403, detail="Permission denied")
    return user

@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    user = User(**payload.dict())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{userid}", response_model=UserOut)
def update_user(
    userid: UUID, 
    payload: UserUpdate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    user = db.query(User).filter(User.id == userid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Admin can edit any user; others only themselves
    if current_user.role != "admin" and current_user.id != userid:
        raise HTTPException(status_code=403, detail="Permission denied")
    for attr, value in payload.dict(exclude_unset=True).items():
        setattr(user, attr, value)
    db.commit()
    db.refresh(user)
    return user

@router.delete("/{userid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    userid: UUID, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == userid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return

@router.get("/me/company-info", response_model=dict)
def get_my_company_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene información de empresa del guía:
    - Si es miembro de una company formal: retorna datos de company table
    - Si es independiente: retorna datos de user.fiscal_data
    """
    if current_user.role != "guide":
        raise HTTPException(status_code=403, detail="Only guides can access company info")
    
    from app.models.companymember import CompanyMember
    from app.models.company import Company
    
    # Verificar si es miembro de una empresa formal
    membership = db.query(CompanyMember).filter(
        CompanyMember.userid == current_user.id,
        CompanyMember.is_active == True
    ).first()
    
    if membership:
        # Guía asociado a empresa
        company = db.query(Company).filter(Company.id == membership.companyid).first()
        return {
            "type": "company_member",
            "company_id": str(company.id),
            "company_name": company.name,
            "is_admin": membership.is_admin,
            "position": membership.position,
            "data": {
                "legal_name": company.legal_name,
                "trade_name": company.trade_name,
                "country": company.country,
                "address": company.address,
            }
        }
    else:
        # Guía independiente
        return {
            "type": "independent",
            "company_id": None,
            "company_name": None,
            "data": current_user.fiscal_data or {}
        }
