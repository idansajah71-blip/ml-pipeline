from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from typing import Optional
import secrets

from app.core.database import get_db
from app.core.security import (
    get_current_active_user, create_access_token, create_refresh_token,
    verify_token, get_password_hash, require_admin,
)
from app.core.redis import cache_set, cache_get, cache_delete
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserResponse, UserLogin, Token, TokenRefresh, UserUpdate, APIKeyResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class EmailVerificationRequest(BaseModel):
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    user = await service.create_user(user_data)
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    service = UserService(db)
    user = await service.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: TokenRefresh, db: AsyncSession = Depends(get_db)):
    payload = verify_token(request.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    from uuid import UUID
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.update_user(current_user.id, user_data)
    return UserResponse.model_validate(user)


@router.post("/api-key", response_model=APIKeyResponse)
async def generate_api_key(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    api_key = await service.generate_api_key(current_user.id)
    return APIKeyResponse(api_key=api_key, message="API key generated successfully")


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    users = await service.get_all_users(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.post("/password-reset-request")
async def request_password_reset(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_user_by_email(request.email)

    if user:
        reset_token = secrets.token_urlsafe(32)
        await cache_set(f"password_reset:{reset_token}", str(user.id), expire=3600)

        return {
            "message": "If the email exists, a password reset link has been sent",
        }

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password-reset-confirm")
async def confirm_password_reset(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    user_id = await cache_get(f"password_reset:{request.token}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    service = UserService(db)
    from uuid import UUID
    user = await service.get_user_by_id(UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(request.new_password)
    await db.flush()
    await cache_delete(f"password_reset:{request.token}")

    return {"message": "Password reset successfully"}


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from app.core.security import verify_password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    await db.flush()

    return {"message": "Password changed successfully"}


@router.post("/verify-email")
async def verify_email(
    request: EmailVerificationRequest,
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    user = await service.get_user_by_email(request.email)

    if user:
        verification_token = secrets.token_urlsafe(32)
        await cache_set(f"email_verify:{verification_token}", str(user.id), expire=86400)

        return {
            "message": "If the email exists, a verification link has been sent",
            "token": verification_token,
        }

    return {"message": "If the email exists, a verification link has been sent"}


@router.post("/verify-email/confirm")
async def confirm_email_verification(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    user_id = await cache_get(f"email_verify:{token}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    service = UserService(db)
    from uuid import UUID
    user = await service.get_user_by_id(UUID(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await cache_delete(f"email_verify:{token}")
    return {"message": "Email verified successfully"}
