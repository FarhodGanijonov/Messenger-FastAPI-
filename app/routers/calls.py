from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.call import CallInitiate, CallResponse, CallHistoryResponse
from app.services.call_service import CallService

router = APIRouter(prefix="/api/calls", tags=["Calls"])


def _format_call(call, db_users: dict) -> dict:
    caller = db_users.get(call.caller_id)
    receiver = db_users.get(call.receiver_id)
    return {
        "id": call.id,
        "caller_id": call.caller_id,
        "receiver_id": call.receiver_id,
        "type": call.type,
        "status": call.status,
        "started_at": call.started_at.isoformat(),
        "accepted_at": call.accepted_at.isoformat() if call.accepted_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "duration_seconds": call.duration_seconds,
        "caller": {"id": caller.id, "full_name": caller.full_name, "avatar_url": caller.avatar_url} if caller else None,
        "receiver": {"id": receiver.id, "full_name": receiver.full_name, "avatar_url": receiver.avatar_url} if receiver else None,
    }


@router.post("/initiate", response_model=dict)
async def initiate_call(
    data: CallInitiate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CallService(db)
    call = await service.initiate_call(current_user.id, data.receiver_id, data.type)
    return {
        "id": call.id,
        "caller_id": call.caller_id,
        "receiver_id": call.receiver_id,
        "type": call.type,
        "status": call.status,
        "started_at": call.started_at.isoformat(),
    }


@router.post("/{call_id}/accept", response_model=dict)
async def accept_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CallService(db)
    call = await service.accept_call(call_id, current_user.id)
    return {"id": call.id, "status": call.status, "accepted_at": call.accepted_at.isoformat()}


@router.post("/{call_id}/reject", response_model=dict)
async def reject_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CallService(db)
    call = await service.reject_call(call_id, current_user.id)
    return {"id": call.id, "status": call.status}


@router.post("/{call_id}/end", response_model=dict)
async def end_call(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CallService(db)
    call = await service.end_call(call_id, current_user.id)
    return {
        "id": call.id,
        "status": call.status,
        "ended_at": call.ended_at.isoformat(),
        "duration_seconds": call.duration_seconds,
    }


@router.get("/history", response_model=dict)
async def get_call_history(
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = CallService(db)
    calls = await service.get_call_history(current_user.id, limit=limit, offset=offset)

    # Collect all unique user IDs
    user_ids = set()
    for call in calls:
        if call.caller_id:
            user_ids.add(call.caller_id)
        if call.receiver_id:
            user_ids.add(call.receiver_id)

    users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users_dict = {u.id: u for u in users_result.scalars().all()}

    return {
        "calls": [_format_call(c, users_dict) for c in calls],
        "total": len(calls),
    }
