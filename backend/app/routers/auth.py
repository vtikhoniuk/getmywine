"""Authentication router."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    UserResponse,
    MessageResponse,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
settings = get_settings()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("3/hour")
async def register(
    request: Request,
    response: Response,
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Register a new user."""
    auth_service = AuthService(db)

    try:
        user, access_token = await auth_service.register(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Set cookie with JWT token
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )

    return user


@router.post("/login", response_model=UserResponse)
@limiter.limit("5/15minutes")
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Login with email and password."""
    auth_service = AuthService(db)

    result = await auth_service.authenticate(data)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    user, access_token = result

    # Set cookie with JWT token
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
    )

    return user


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Logout current user."""
    # Delete cookie
    response.delete_cookie(key="access_token")

    return MessageResponse(message="Вы успешно вышли из системы")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Get current user."""
    return current_user


@router.post("/password-reset/request", response_model=MessageResponse)
@limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    data: PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Request password reset email."""
    auth_service = AuthService(db)

    token = await auth_service.request_password_reset(data.email)

    if token:
        # TODO: Send email with reset link
        # email_service.send_password_reset(data.email, token)
        pass

    # Always return same message to prevent email enumeration
    return MessageResponse(
        message="Если email существует в системе, письмо со ссылкой для сброса пароля отправлено"
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    data: PasswordResetConfirm,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Confirm password reset with token."""
    auth_service = AuthService(db)

    success = await auth_service.confirm_password_reset(
        data.token, data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невалидный или истёкший токен",
        )

    return MessageResponse(message="Пароль успешно изменён")
