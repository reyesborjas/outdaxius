from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from uuid import uuid4

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.db.config import SECRET_KEY, ALGORITHM

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Token config
ACCESS_MINUTES = 30
REFRESH_DAYS = 15

# Simple in-memory rotation store (replace with DB in producción)
_invalidated_jti = set()

def create_token(
    data: dict,
    *,
    kind: Literal["access", "refresh", "reset"],
    exp: Optional[timedelta] = None,
) -> str:
    to_encode = data.copy()
    jti = str(uuid4())
    now = datetime.now(timezone.utc)
    if kind == "access":
        expire = now + (exp or timedelta(minutes=ACCESS_MINUTES))
    elif kind == "refresh":
        expire = now + (exp or timedelta(days=REFRESH_DAYS))
    elif kind == "reset":
        expire = now + (exp or timedelta(hours=1))
    else:
        raise ValueError("invalid token kind")
    to_encode.update({"exp": expire, "iat": now, "jti": jti, "typ": kind})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str, *, expected: Optional[Literal["access","refresh","reset"]] = None) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("jti") in _invalidated_jti:
        raise JWTError("token revoked")
    if expected and payload.get("typ") != expected:
        raise JWTError("unexpected token type")
    return payload

def rotate_refresh(old_token: str) -> str:
    payload = decode_token(old_token, expected="refresh")
    _invalidated_jti.add(payload["jti"])  # revoke old
    # keep only minimal subject claims
    sub = {k: payload[k] for k in ("sub", "email", "role") if k in payload}
    return create_token(sub, kind="refresh")
