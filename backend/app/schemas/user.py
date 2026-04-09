import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="viewer", pattern=r"^(viewer|creator|admin|super_admin)$")
    market_id: uuid.UUID | None = None
    is_active: bool = True


class UserCreate(UserBase):
    oauth_provider_id: str | None = None


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(
        default=None, pattern=r"^(viewer|creator|admin|super_admin)$"
    )
    market_id: uuid.UUID | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str
    market_id: uuid.UUID | None = None
    is_active: bool
    oauth_provider_id: str | None = None
    created_at: datetime
    updated_at: datetime


class UserBrief(BaseModel):
    """Lightweight user representation for embedding in other responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: str


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int


# --- Auth / Token schemas ---


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
    role: str
    market_id: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        ..., description="Token lifetime in seconds"
    )
    user: UserResponse


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class OAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    expires_at: datetime
    ip_address: str | None = None
