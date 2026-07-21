# app/api/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional, Any, Dict
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserOut
from app.core.security import (
    get_password_hash, verify_password,
    create_token, decode_token, rotate_refresh,
)
from app.services.personal_team import ensure_personal_team

router = APIRouter()

# ======== Rate limiting e intentos ========
FAILED_WINDOW = timedelta(minutes=15)
LOCK_MINUTES = 15
MAX_FAILED = 5

_failed_map = {}  # key -> list[datetime]
_locked_until = {}  # key -> datetime

def _key(req: Request, email: str) -> str:
    ip = req.client.host if req.client else "unknown"
    return f"{ip}|{email.lower()}"

def _is_locked(k: str) -> Optional[datetime]:
    u = _locked_until.get(k)
    if u and u > datetime.now(timezone.utc):
        return u
    _locked_until.pop(k, None)
    return None

def _register_fail(k: str):
    now = datetime.now(timezone.utc)
    arr = [t for t in _failed_map.get(k, []) if now - t <= FAILED_WINDOW]
    arr.append(now)
    _failed_map[k] = arr
    if len(arr) >= MAX_FAILED:
        _locked_until[k] = now + timedelta(minutes=LOCK_MINUTES)
        _failed_map[k] = []

def _clear_fail(k: str):
    _failed_map.pop(k, None)
    _locked_until.pop(k, None)

# ======== Schemas ========
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    # "client" matches the live user_role DB enum (admin/guide/client) -- was "user" here, which
    # the enum has never accepted since the Phase 2 migration renamed it, so every traveler
    # self-registration 500'd.
    role: Literal["client", "guide"] = "client"
    # Optional guide fields
    passport_number: Optional[str] = None
    phone: Optional[str] = None
    profile: Optional[Dict[str, Any]] = None
    # Company guide fields
    tax_id: Optional[str] = None
    fiscal_data: Optional[Dict[str, Any]] = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class LoginOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut

class RefreshIn(BaseModel):
    refresh_token: str

class PasswordResetRequestIn(BaseModel):
    email: EmailStr

class PasswordResetIn(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

# ======== Register ========
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Validate company guide requirements
    if payload.role == "guide":
        has_fiscal = payload.fiscal_data and isinstance(payload.fiscal_data, dict)
        has_tax_id = payload.tax_id and isinstance(payload.tax_id, str) and len(payload.tax_id.strip()) > 0
        
        if has_fiscal or has_tax_id:
            # Company guide: require both tax_id and fiscal_data
            if not has_tax_id:
                raise HTTPException(status_code=422, detail="tax_id is required for company guides")
            if not has_fiscal:
                raise HTTPException(status_code=422, detail="fiscal_data is required for company guides")
            
            # Validate fiscal_data structure (minimal check)
            fd = payload.fiscal_data
            if not fd.get("tax_identification", {}).get("primary_identification_number"):
                raise HTTPException(
                    status_code=422,
                    detail="fiscal_data.tax_identification.primary_identification_number is required"
                )

    user = User(
        display_name=payload.display_name,
        email=payload.email,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        first_name=payload.first_name,
        last_name=payload.last_name,
        passport_number=payload.passport_number,
        phone=payload.phone,
        tax_id=payload.tax_id,
        profile=payload.profile or {},
        fiscal_data=payload.fiscal_data or {},
        birth_date=None,
        preferred_language="en",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Every guide always holds a team -- see app.services.personal_team for why. Travelers
    # ("user" role) and admins (created out-of-band, never through this endpoint) don't need one.
    if user.role == "guide":
        ensure_personal_team(db, user)
        db.commit()

    return user

# ======== Login con rate-limit ========
@router.post("/login", response_model=LoginOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    k = _key(request, data.email)
    locked = _is_locked(k)
    if locked:
        remaining = int((locked - datetime.now(timezone.utc)).total_seconds() // 60) + 1
        raise HTTPException(status_code=429, detail=f"Demasiados intentos. Intenta en ~{remaining} min")

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        _register_fail(k)
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    _clear_fail(k)
    sub = {"sub": str(user.id), "email": user.email, "role": user.role}
    access = create_token(sub, kind="access")
    refresh = create_token(sub, kind="refresh")
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer", "user": user}

# ======== Refresh con rotación ========
@router.post("/refresh")
def refresh_token(payload: RefreshIn):
    new_refresh = rotate_refresh(payload.refresh_token)
    claims = decode_token(new_refresh, expected="refresh")
    sub = {k: claims[k] for k in ("sub", "email", "role")}
    new_access = create_token(sub, kind="access")
    return {"access_token": new_access, "refresh_token": new_refresh}

# ======== Password recovery ========
@router.post("/request-password-reset")
def request_password_reset(payload: PasswordResetRequestIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        sub = {"sub": str(user.id), "email": user.email}
        token = create_token(sub, kind="reset")
        # TODO: enviar email con el token
        return {"status": "ok", "token_preview": token[:24]}
    return {"status": "ok"}

@router.post("/reset-password")
def reset_password(payload: PasswordResetIn, db: Session = Depends(get_db)):
    claims = decode_token(payload.token, expected="reset")
    uid = claims.get("sub")
    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=400, detail="Token inválido")
    user.password_hash = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()
    return {"status": "ok"}
