"""Pydantic schemas for authentication."""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)
    is_age_verified: bool

    @field_validator("is_age_verified")
    @classmethod
    def age_must_be_verified(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Вы должны подтвердить, что вам исполнилось 18 лет")
        return v


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    """Request schema for password reset."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Request schema for password reset confirmation."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=72)


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: uuid.UUID
    email: EmailStr
    is_age_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class ErrorResponse(BaseModel):
    """Error response schema."""

    detail: str


class RateLimitResponse(BaseModel):
    """Rate limit exceeded response."""

    detail: str
    retry_after: int
