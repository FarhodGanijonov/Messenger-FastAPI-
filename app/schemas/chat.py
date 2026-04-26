from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChatCreate(BaseModel):
    type: str = "direct"  # direct, group
    name: Optional[str] = None
    member_ids: List[str]


class ChatResponse(BaseModel):
    id: str
    type: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    member_count: Optional[int] = None
    last_message: Optional[dict] = None
    unread_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ChatDetailResponse(BaseModel):
    id: str
    type: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime
    members: List[dict] = []

    class Config:
        from_attributes = True


class ChatMemberResponse(BaseModel):
    id: str
    user_id: str
    role: str
    joined_at: datetime
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True
