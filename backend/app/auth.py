import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .db import get_db
from .models.user import User


SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me")
TOKEN_TTL_SECONDS = int(os.getenv("TOKEN_TTL_SECONDS", "86400"))
BOOTSTRAP_ADMIN_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "").strip().lower()
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
BOOTSTRAP_ADMIN_DISPLAY_NAME = os.getenv("BOOTSTRAP_ADMIN_DISPLAY_NAME", "")
BOOTSTRAP_CLASS_USERS = os.getenv("BOOTSTRAP_CLASS_USERS", "false").strip().lower() in {"1", "true", "yes", "on"}
BOOTSTRAP_CLASS_PASSWORD = os.getenv("BOOTSTRAP_CLASS_PASSWORD", "classe123")

ROLE_WEIGHTS = {
    "contributor": 0.25,
    "teacher": 1.5,
    "learner": 0.25,
    "admin": 2.5,
}

LEVEL_FACTORS = {
    "undefined": 0.8,
    "A1": 0.5,
    "A2": 0.6,
    "B1": 0.8,
    "B2": 1.0,
    "C1": 1.15,
    "C2": 1.25,
    "native": 1.35,
}

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt_b64, digest_b64 = stored.split("$", 2)
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def validation_weight_for(user: Optional[User]) -> float:
    if not user:
        return 0.1
    role_weight = ROLE_WEIGHTS.get(user.role, 0.25)
    level_factor = LEVEL_FACTORS.get(user.breton_level or "undefined", 0.8)
    return round(role_weight * level_factor, 2)


def user_to_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "breton_level": user.breton_level,
        "organization": user.organization,
        "school": user.school,
        "school_level": user.school_level,
        "comments": user.notes,
        "must_change_password": user.must_change_password,
        "active": user.active,
        "created_at": user.created_at,
        "validation_weight": validation_weight_for(user),
    }


def create_access_token(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = _sign(body)
    return f"{body}.{signature}"


def decode_access_token(token: str) -> dict:
    try:
        body, signature = token.split(".", 1)
        if not hmac.compare_digest(_sign(body), signature):
            raise ValueError("bad signature")
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ValueError("expired")
        return payload
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    user = get_optional_user(authorization=authorization, db=db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    payload = decode_access_token(token)
    user_id = int(payload["sub"])
    return db.query(User).filter(User.id == user_id, User.active == True).first()


def _sign(body: str) -> str:
    digest = hmac.new(SECRET_KEY.encode(), body.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")
