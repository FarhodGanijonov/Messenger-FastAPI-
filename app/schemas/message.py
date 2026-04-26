from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MessageCreate(BaseModel):
    type: str = "text"  # text, image, video, audio, file
    content: Optional[str] = None
    media_id: Optional[str] = None
    reply_to_id: Optional[str] = None


class MessageResponse(BaseModel):
    id: str
    chat_id: str
    sender_id: Optional[str] = None
    type: str
    content: Optional[str] = None
    media_url: Optional[str] = None
    reply_to_id: Optional[str] = None
    is_read: bool
    is_deleted: bool
    created_at: datetime
    sender: Optional[dict] = None

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    messages: List[MessageResponse]
    next_cursor: Optional[str] = None
    has_more: bool = False


class ReadReceiptRequest(BaseModel):
    message_ids: Optional[List[str]] = None  # if None, mark all as read
