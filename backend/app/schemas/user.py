from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal, Optional


class UserRead(BaseModel):
    id: int
    email: str
    display_name: str
    role: str
    breton_level: str
    organization: Optional[str] = None
    school: Optional[str] = None
    school_level: Optional[str] = None
    comments: Optional[str] = None
    must_change_password: bool = False
    active: bool
    created_at: datetime
    validation_weight: float

    class Config:
        from_attributes = True


class UserRegister(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    breton_level: str = "undefined"
    organization: Optional[str] = None
    comments: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class UserAdminCreate(UserRegister):
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    role: Literal['admin', 'teacher', 'contributor', 'learner'] = 'contributor'
    breton_level: Literal['undefined', 'A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'native'] = 'undefined'
    must_change_password: bool = True


class PasswordChangeRequest(BaseModel):
    new_password: str = Field(min_length=8, max_length=128)


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    breton_level: Optional[str] = None
    organization: Optional[str] = None
    comments: Optional[str] = None


class UserAdminUpdate(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[str] = None
    breton_level: Optional[str] = None
    organization: Optional[str] = None
    school: Optional[str] = None
    school_level: Optional[str] = None
    comments: Optional[str] = None
    must_change_password: Optional[bool] = None
    active: Optional[bool] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
