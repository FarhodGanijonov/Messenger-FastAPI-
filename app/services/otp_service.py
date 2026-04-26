import random
import string
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.user import OTPCode
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class OTPService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_code(self) -> str:
        return "".join(random.choices(string.digits, k=6))

    async def generate_otp(self, phone: str) -> str:
        # Invalidate previous OTPs for this phone
        await self.db.execute(
            update(OTPCode)
            .where(OTPCode.phone == phone, OTPCode.is_used == False)
            .values(is_used=True)
        )

        code = self._generate_code()
        expires_at = datetime.utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        otp = OTPCode(
            phone=phone,
            code=code,
            expires_at=expires_at,
        )
        self.db.add(otp)
        await self.db.flush()

        return code

    async def verify_otp(self, phone: str, code: str) -> bool:
        result = await self.db.execute(
            select(OTPCode).where(
                OTPCode.phone == phone,
                OTPCode.code == code,
                OTPCode.is_used == False,
                OTPCode.expires_at > datetime.utcnow(),
            )
        )
        otp = result.scalar_one_or_none()

        if not otp:
            return False

        otp.is_used = True
        await self.db.flush()
        return True

    async def send_sms(self, phone: str, code: str) -> bool:
        if settings.OTP_DEV_MODE:
            logger.info(f"[DEV MODE] OTP for {phone}: {code}")
            return True

        # Production: Use Twilio
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            message = client.messages.create(
                body=f"Your verification code is: {code}. Valid for {settings.OTP_EXPIRE_MINUTES} minutes.",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone,
            )
            logger.info(f"SMS sent to {phone}, SID: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {e}")
            return False
