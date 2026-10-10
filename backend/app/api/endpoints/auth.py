from typing import List
from datetime import datetime, timedelta
from email.message import EmailMessage
import secrets
import hashlib
import os
from urllib.parse import urlsplit
import smtplib
from fastapi import Request
from pydantic import BaseModel, Field
from ...password_email import EmailLimiter, deliver, smtp_settings, SENDER

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...auth import create_access_token, get_current_user, hash_password, require_admin, user_to_payload, verify_password
from ...db import get_db
from ...models.user import User
from ...schemas.user import UserAdminCreate
from sqlalchemy.exc import IntegrityError
from ...schemas.user import LoginRequest, PasswordChangeRequest, TokenResponse, UserAdminUpdate, UserProfileUpdate, UserRead, UserRegister

router = APIRouter()

ALLOWED_ROLES = {"admin", "teacher", "contributor", "learner"}
ALLOWED_BRETON_LEVELS = {"undefined", "A1", "A2", "B1", "B2", "C1", "C2", "native"}
reset_limiter = EmailLimiter()


class ForgotPasswordRequest(BaseModel):
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@router.post("/forgot-password", status_code=202)
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    settings = smtp_settings("PASSWORD_RESET_EMAIL_ENABLED")
    base = os.getenv("PASSWORD_RESET_URL", "http://127.0.0.1:4200/reinitialiser-mot-de-passe")
    parsed = urlsplit(base)
    if not parsed.hostname or parsed.query or parsed.fragment or parsed.username or not (parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost"})):
        raise HTTPException(503, "reset_url_not_configured")
    email = payload.email.lower()
    reset_limiter.reserve("ip:" + (request.client.host if request.client else "unknown"))
    reset_limiter.reserve("email:" + email)
    user = db.query(User).filter(User.email == email, User.active == True).with_for_update().first()
    if user:
        token = secrets.token_urlsafe(32)
        link = base + "#token=" + token
        message = EmailMessage()
        message['From'] = f'KeltiaWave <{SENDER}>'
        message['To'] = user.email
        message['Subject'] = 'Choisissez un nouveau mot de passe KeltiaWave'
        message.set_content(f'Pour choisir votre nouveau mot de passe, ouvrez ce lien :\n\n{link}\n\n'
                            'Ce lien est valable 30 minutes et utilisable une seule fois.\n'
                            'Si vous n’avez pas demandé ce message, ignorez-le : votre mot de passe reste inchangé.\n')
        try:
            deliver(message, settings)
        except (smtplib.SMTPException, OSError):
            db.rollback()
            # Same public response for unknown accounts and delivery failures.
            return {"status": "accepted"}
        user.temporary_password_hash = "reset$" + hashlib.sha256(token.encode()).hexdigest()
        user.temporary_password_expires_at = datetime.utcnow() + timedelta(minutes=30)
        db.commit()
    return {"status": "accepted"}


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    digest = "reset$" + hashlib.sha256(payload.token.encode()).hexdigest()
    user = db.query(User).filter(User.temporary_password_hash == digest, User.active == True).with_for_update().first()
    if not user or not user.temporary_password_expires_at or user.temporary_password_expires_at <= datetime.utcnow():
        raise HTTPException(400, "reset_link_invalid_or_expired")
    user.password_hash = hash_password(payload.new_password)
    user.temporary_password_hash = None
    user.temporary_password_expires_at = None
    user.must_change_password = False
    user.auth_version = (user.auth_version or 0) + 1
    db.commit()
    return {"status": "password_changed"}


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    email = payload.email.lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    if payload.breton_level not in ALLOWED_BRETON_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid Breton level")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip(),
        profile_type="contributor",
        role="contributor",
        breton_level=payload.breton_level,
        organization=payload.organization or None,
        notes=payload.comments or None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user), "user": user_to_payload(user)}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.active:
        raise HTTPException(status_code=403, detail="Inactive account")
    return {"access_token": create_access_token(user), "user": user_to_payload(user)}


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user_to_payload(user)


@router.patch("/me", response_model=UserRead)
def update_me(
    payload: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patch = payload.model_dump(exclude_unset=True)
    if patch.get("breton_level") not in (None, *ALLOWED_BRETON_LEVELS):
        raise HTTPException(status_code=400, detail="Invalid Breton level")

    comments = patch.pop("comments", None) if "comments" in patch else user.notes
    for key, value in patch.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(user, key, value)
    user.notes = comments.strip() or None if isinstance(comments, str) else comments

    db.commit()
    db.refresh(user)
    return user_to_payload(user)


@router.post("/change-password", response_model=UserRead)
def change_password(
    payload: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    user.temporary_password_hash = None
    user.temporary_password_expires_at = None
    db.commit()
    db.refresh(user)
    return user_to_payload(user)


@router.get("/users", response_model=List[UserRead])
def list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.created_at.desc(), User.id.desc()).all()
    return [user_to_payload(user) for user in users]


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(payload: UserAdminCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    email = payload.email.lower()
    if not payload.display_name.strip():
        raise HTTPException(status_code=422, detail="Display name is required")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=email, password_hash=hash_password(payload.password),
                display_name=payload.display_name.strip(), role=payload.role,
                profile_type=payload.role, breton_level=payload.breton_level,
                organization=payload.organization or None, notes=payload.comments or None,
                must_change_password=payload.must_change_password, active=True)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.refresh(user)
    return user_to_payload(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserAdminUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    patch = payload.model_dump(exclude_unset=True)
    if patch.get("role") not in (None, *ALLOWED_ROLES):
        raise HTTPException(status_code=400, detail="Invalid role")
    if patch.get("breton_level") not in (None, *ALLOWED_BRETON_LEVELS):
        raise HTTPException(status_code=400, detail="Invalid Breton level")

    comments = patch.pop("comments", None) if "comments" in patch else user.notes
    for key, value in patch.items():
        if isinstance(value, str):
            value = value.strip() or None
        setattr(user, key, value)
    user.notes = comments.strip() or None if isinstance(comments, str) else comments

    if user.id == admin.id and user.role != "admin":
        raise HTTPException(status_code=400, detail="You cannot remove your own admin role")
    if user.id == admin.id and user.active is False:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    db.commit()
    db.refresh(user)
    return user_to_payload(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
