from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class Call(Base):
    __tablename__ = "calls"

    id = Column(String, primary_key=True, default=gen_uuid)
    caller_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    receiver_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(10), nullable=False, default="audio")  # audio, video
    status = Column(String(20), nullable=False, default="initiated")  # initiated, accepted, rejected, ended, missed
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Relationships
    caller = relationship("User", back_populates="initiated_calls", foreign_keys=[caller_id])
    receiver = relationship("User", back_populates="received_calls", foreign_keys=[receiver_id])
