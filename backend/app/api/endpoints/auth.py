from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...auth import create_access_token, get_current_user, hash_password, require_admin, user_to_payload, verify_password
from ...db import get_db
from ...models.user import User
from ...schemas.user import LoginRequest, PasswordChangeRequest, TokenResponse, UserAdminUpdate, UserProfileUpdate, UserRead, UserRegister

router = APIRouter()

ALLOWED_ROLES = {"admin", "teacher", "contributor", "learner"}
ALLOWED_BRETON_LEVELS = {"undefined", "A1", "A2", "B1", "B2", "C1", "C2", "native"}


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
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid current password")

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
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
