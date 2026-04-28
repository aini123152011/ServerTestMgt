from pydantic import BaseModel, EmailStr

from app.models.user import UserRole
from app.schemas.common import TimestampSchema


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: str | None = None
    role: UserRole = UserRole.TESTER


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(TimestampSchema):
    id: int
    username: str
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
