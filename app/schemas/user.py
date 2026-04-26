from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None


class UserCreate(UserBase):
    phone: str


class ProfileSetup(BaseModel):
    full_name: str
    bio: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    phone: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    last_seen: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserPublicResponse(BaseModel):
    id: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationSettingsSchema(BaseModel):
    message_notifications: bool = True
    call_notifications: bool = True
    group_notifications: bool = True
    sound_enabled: bool = True
    vibration_enabled: bool = True

    class Config:
        from_attributes = True


class PrivacySettingsSchema(BaseModel):
    last_seen_visible: str = "everyone"
    avatar_visible: str = "everyone"
    bio_visible: str = "everyone"
    read_receipts: bool = True

    class Config:
        from_attributes = True


class DeviceRegisterRequest(BaseModel):
    fcm_token: str
    platform: str  # ios, android, web


class ContactSyncRequest(BaseModel):
    phones: list[str]


class ContactResponse(BaseModel):
    id: str
    contact_id: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: str
    display_name: Optional[str] = None

    class Config:
        from_attributes = True
