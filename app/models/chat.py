from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class ChatType(str, enum.Enum):
    DIRECT = "direct"
    GROUP = "group"


class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=gen_uuid)
    type = Column(String(20), nullable=False, default=ChatType.DIRECT)
    name = Column(String(100), nullable=True)  # for group chats
    avatar_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    created_by = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("ChatMember", back_populates="chat", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class ChatMember(Base):
    __tablename__ = "chat_members"

    id = Column(String, primary_key=True, default=gen_uuid)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), default="member")  # admin, member
    is_muted = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    chat = relationship("Chat", back_populates="members")
    user = relationship("User", back_populates="chat_memberships")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String, primary_key=True, default=gen_uuid)
    owner_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    display_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", foreign_keys=[owner_id])
    contact = relationship("User", foreign_keys=[contact_id])
