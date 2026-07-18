# backeend/api/roles.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from app.db.session import get_db
from app.models.user import UserRole, User
from app.api.deps import get_current_user, require_admin


router = APIRouter(tags=["roles"])

@router.get("/", response_model=List[str])
def list_roles(current_user: User = Depends(get_current_user)):
    # Retorna todos los roles disponibles
    return [role.value for role in UserRole]

@router.post("/assign", status_code=status.HTTP_200_OK)
def assign_role(
    userid: UUID,
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == userid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in [r.value for r in UserRole]:
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = role
    db.commit()
    db.refresh(user)
    return {"status": "ok", "userid": str(userid), "role": role}
