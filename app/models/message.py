from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=gen_uuid)
    chat_id = Column(String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(20), nullable=False, default="text")  # text, image, video, audio, file
    content = Column(Text, nullable=True)
    media_url = Column(String(500), nullable=True)
    media_id = Column(String, ForeignKey("media_files.id", ondelete="SET NULL"), nullable=True)
    reply_to_id = Column(String, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)
    is_read = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    media = relationship("MediaFile", foreign_keys=[media_id])
    reply_to = relationship("Message", remote_side="Message.id", foreign_keys=[reply_to_id])


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(String, primary_key=True, default=gen_uuid)
    uploader_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # image/jpeg, video/mp4, etc.
    file_size = Column(Integer, nullable=False)  # bytes
    storage_type = Column(String(20), default="local")  # local, s3
    file_path = Column(String(500), nullable=False)
    url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    uploader = relationship("User", foreign_keys=[uploader_id])
