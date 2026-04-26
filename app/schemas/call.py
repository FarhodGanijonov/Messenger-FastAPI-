from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CallInitiate(BaseModel):
    receiver_id: str
    type: str = "audio"  # audio, video


class CallResponse(BaseModel):
    id: str
    caller_id: Optional[str] = None
    receiver_id: Optional[str] = None
    type: str
    status: str
    started_at: datetime
    accepted_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    caller: Optional[dict] = None
    receiver: Optional[dict] = None

    class Config:
        from_attributes = True


class CallHistoryResponse(BaseModel):
    calls: List[CallResponse]
    total: int
