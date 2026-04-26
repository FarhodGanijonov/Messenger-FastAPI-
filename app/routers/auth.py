from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.auth import (
    SendOTPRequest, SendOTPResponse,
    VerifyOTPRequest, TokenResponse,
    RefreshTokenRequest, LogoutRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(request: SendOTPRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.send_otp(request.phone)
    return result


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(request: VerifyOTPRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    result = await service.verify_otp(request.phone, request.code)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code",
        )

    user, is_new_user = result
    tokens = await service.create_tokens(user.id)

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        user_id=user.id,
        is_new_user=is_new_user,
    )


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    tokens = await service.refresh_tokens(request.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    from app.core.security import verify_refresh_token
    user_id = verify_refresh_token(request.refresh_token)

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        user_id=user_id or "",
    )


@router.post("/logout")
async def logout(request: LogoutRequest, db: AsyncSession = Depends(get_db)):
    service = AuthService(db)
    await service.logout(request.refresh_token)
    return {"message": "Logged out successfully"}
