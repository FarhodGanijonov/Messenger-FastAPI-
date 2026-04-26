from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.models.user import User, OTPCode, RefreshToken, NotificationSettings, PrivacySettings
from app.core.security import create_access_token, create_refresh_token, verify_refresh_token
from app.config import settings
from app.services.otp_service import OTPService
import uuid


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.otp_service = OTPService(db)

    async def send_otp(self, phone: str) -> dict:
        otp_code = await self.otp_service.generate_otp(phone)
        sms_sent = await self.otp_service.send_sms(phone, otp_code)

        response = {
            "message": "OTP sent successfully",
            "phone": phone,
        }

        if settings.OTP_DEV_MODE:
            response["dev_code"] = otp_code

        return response

    async def verify_otp(self, phone: str, code: str) -> Optional[Tuple[User, bool]]:
        is_valid = await self.otp_service.verify_otp(phone, code)
        if not is_valid:
            return None

        # Get or create user
        result = await self.db.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()
        is_new_user = False

        if not user:
            user = User(
                id=str(uuid.uuid4()),
                phone=phone,
                is_active=True,
            )
            self.db.add(user)

            # Create default settings
            notif_settings = NotificationSettings(user_id=user.id)
            privacy_settings = PrivacySettings(user_id=user.id)
            self.db.add(notif_settings)
            self.db.add(privacy_settings)
            await self.db.flush()
            is_new_user = True

        # Update last seen
        user.last_seen = datetime.utcnow()
        await self.db.flush()

        return user, is_new_user

    async def create_tokens(self, user_id: str) -> dict:
        access_token = create_access_token({"sub": user_id})
        refresh_token = create_refresh_token({"sub": user_id})

        # Save refresh token
        expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        rt = RefreshToken(
            user_id=user_id,
            token=refresh_token,
            expires_at=expires_at,
        )
        self.db.add(rt)
        await self.db.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }

    async def refresh_tokens(self, refresh_token: str) -> Optional[dict]:
        user_id = verify_refresh_token(refresh_token)
        if not user_id:
            return None

        # Check token in DB
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token == refresh_token,
                RefreshToken.is_revoked == False,
                RefreshToken.expires_at > datetime.utcnow(),
            )
        )
        db_token = result.scalar_one_or_none()
        if not db_token:
            return None

        # Revoke old token
        db_token.is_revoked = True
        await self.db.flush()

        # Create new tokens
        return await self.create_tokens(user_id)

    async def logout(self, refresh_token: str) -> bool:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == refresh_token)
        )
        db_token = result.scalar_one_or_none()
        if db_token:
            db_token.is_revoked = True
            await self.db.flush()
        return True
