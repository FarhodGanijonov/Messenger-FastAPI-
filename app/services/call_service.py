from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
from datetime import datetime
from app.models.call import Call
from app.models.user import User
from app.core.websocket_manager import manager
import uuid


class CallService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def initiate_call(self, caller_id: str, receiver_id: str, call_type: str) -> Call:
        # Check receiver exists
        result = await self.db.execute(select(User).where(User.id == receiver_id))
        receiver = result.scalar_one_or_none()
        if not receiver:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Receiver not found")

        call = Call(
            id=str(uuid.uuid4()),
            caller_id=caller_id,
            receiver_id=receiver_id,
            type=call_type,
            status="initiated",
        )
        self.db.add(call)
        await self.db.flush()

        # Get caller info
        caller_result = await self.db.execute(select(User).where(User.id == caller_id))
        caller = caller_result.scalar_one_or_none()

        # Notify receiver
        await manager.send_call_event(receiver_id, {
            "call_id": call.id,
            "caller_id": caller_id,
            "caller_name": caller.full_name if caller else None,
            "caller_avatar": caller.avatar_url if caller else None,
            "type": call_type,
            "status": "initiated",
        })

        return call

    async def accept_call(self, call_id: str, user_id: str) -> Optional[Call]:
        result = await self.db.execute(
            select(Call).where(Call.id == call_id, Call.receiver_id == user_id)
        )
        call = result.scalar_one_or_none()
        if not call:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Call not found")

        if call.status != "initiated":
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Call is not in initiated state")

        call.status = "accepted"
        call.accepted_at = datetime.utcnow()
        await self.db.flush()

        # Notify caller
        await manager.send_to_user(call.caller_id, "call.accepted", {
            "call_id": call_id,
            "accepted_by": user_id,
        })

        return call

    async def reject_call(self, call_id: str, user_id: str) -> Optional[Call]:
        result = await self.db.execute(
            select(Call).where(Call.id == call_id, Call.receiver_id == user_id)
        )
        call = result.scalar_one_or_none()
        if not call:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Call not found")

        call.status = "rejected"
        call.ended_at = datetime.utcnow()
        await self.db.flush()

        await manager.send_to_user(call.caller_id, "call.rejected", {
            "call_id": call_id,
            "rejected_by": user_id,
        })

        return call

    async def end_call(self, call_id: str, user_id: str) -> Optional[Call]:
        result = await self.db.execute(
            select(Call).where(
                Call.id == call_id,
                (Call.caller_id == user_id) | (Call.receiver_id == user_id),
            )
        )
        call = result.scalar_one_or_none()
        if not call:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Call not found")

        call.status = "ended"
        call.ended_at = datetime.utcnow()

        if call.accepted_at:
            delta = call.ended_at - call.accepted_at
            call.duration_seconds = int(delta.total_seconds())

        await self.db.flush()

        # Notify both parties
        other_user_id = call.receiver_id if call.caller_id == user_id else call.caller_id
        await manager.send_to_user(other_user_id, "call.ended", {
            "call_id": call_id,
            "ended_by": user_id,
            "duration_seconds": call.duration_seconds,
        })

        return call

    async def get_call_history(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Call]:
        result = await self.db.execute(
            select(Call)
            .where(
                (Call.caller_id == user_id) | (Call.receiver_id == user_id)
            )
            .order_by(desc(Call.started_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
