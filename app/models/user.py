from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    sent_messages = relationship("Message", back_populates="sender", foreign_keys="Message.sender_id")
    chat_memberships = relationship("ChatMember", back_populates="user")
    initiated_calls = relationship("Call", back_populates="caller", foreign_keys="Call.caller_id")
    received_calls = relationship("Call", back_populates="receiver", foreign_keys="Call.receiver_id")
    otp_codes = relationship("OTPCode", back_populates="user_ref", foreign_keys="OTPCode.phone", primaryjoin="User.phone == OTPCode.phone")
    devices = relationship("Device", back_populates="user")
    notification_settings = relationship("NotificationSettings", back_populates="user", uselist=False)
    privacy_settings = relationship("PrivacySettings", back_populates="user", uselist=False)


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(String, primary_key=True, default=gen_uuid)
    phone = Column(String(20), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_ref = relationship("User", back_populates="otp_codes", foreign_keys=[phone], primaryjoin="OTPCode.phone == User.phone")


class Device(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fcm_token = Column(String(500), nullable=False)
    platform = Column(String(20), nullable=False)  # ios, android, web
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="devices")


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    message_notifications = Column(Boolean, default=True)
    call_notifications = Column(Boolean, default=True)
    group_notifications = Column(Boolean, default=True)
    sound_enabled = Column(Boolean, default=True)
    vibration_enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="notification_settings")


class PrivacySettings(Base):
    __tablename__ = "privacy_settings"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    last_seen_visible = Column(String(20), default="everyone")  # everyone, contacts, nobody
    avatar_visible = Column(String(20), default="everyone")
    bio_visible = Column(String(20), default="everyone")
    read_receipts = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="privacy_settings")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
