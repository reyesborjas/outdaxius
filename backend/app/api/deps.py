# backend/app/api/deps.py
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.db.session import get_db
from app.db.config import SECRET_KEY, ALGORITHM
from app.models.user import User
from fastapi import Depends, HTTPException, status, Request
import uuid
from app.models.companymember import CompanyMember

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
# auto_error=False: resolves to None instead of raising when no Authorization header is sent --
# for endpoints that are public by default but behave differently for an authenticated caller
# (e.g. list_program_schedules's mine_only param).
_oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise credentials_exception
    return user

def get_current_user_optional(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(_oauth2_scheme_optional),
) -> Optional[User]:
    """Like get_current_user, but returns None instead of 401 when no/invalid token is sent."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        return None
    return user

def require_role(required: set):
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in required:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return current_user
    return dependency

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin-only")
    return current_user

def get_current_company_id(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Company context:
    - If X-Company-Id header is present -> validate membership and return it.
    - Else if user has exactly 1 active company membership -> return it.
    - Else if user has 0 memberships -> return None (solo guides / legacy behavior).
    - Else (multiple memberships) -> require header to avoid ambiguity.
    """
    header = request.headers.get("X-Company-Id") or request.headers.get("x-company-id")
    if header:
        try:
            company_id = uuid.UUID(header)
        except Exception:
            raise HTTPException(400, detail="Invalid X-Company-Id header")

        if current_user.role == "admin":
            return company_id

        member = db.query(CompanyMember).filter(
            CompanyMember.companyid == company_id,
            CompanyMember.userid == current_user.id,
            CompanyMember.is_active == True
        ).first()
        if not member:
            raise HTTPException(403, detail="Not a member of this company (X-Company-Id)")
        return company_id

    active = db.query(CompanyMember.companyid).filter(
        CompanyMember.userid == current_user.id,
        CompanyMember.is_active == True
    ).distinct().all()
    company_ids = [r[0] for r in active]

    if len(company_ids) == 1:
        return company_ids[0]
    if len(company_ids) == 0:
        return None

    raise HTTPException(
        400,
        detail="Multiple companies found. Send X-Company-Id header."
    )