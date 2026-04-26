from pydantic import BaseModel, validator
import re
from typing import Optional


class SendOTPRequest(BaseModel):
    phone: str

    @validator("phone")
    def validate_phone(cls, v):
        v = re.sub(r"\s+", "", v)
        if not re.match(r"^\+?[1-9]\d{7,14}$", v):
            raise ValueError("Invalid phone number format")
        return v


class VerifyOTPRequest(BaseModel):
    phone: str
    code: str

    @validator("code")
    def validate_code(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be 6 digits")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    is_new_user: bool = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SendOTPResponse(BaseModel):
    message: str
    phone: str
    dev_code: Optional[str] = None  # Only in dev mode


class LogoutRequest(BaseModel):
    refresh_token: str
