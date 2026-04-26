from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.message import MessageCreate, MessageResponse, MessageListResponse, ReadReceiptRequest
from app.services.message_service import MessageService

router = APIRouter(prefix="/api/chats", tags=["Messages"])


@router.get("/{chat_id}/messages", response_model=MessageListResponse)
async def get_messages(
    chat_id: str,
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    messages, next_cursor, has_more = await service.get_chat_messages(
        chat_id=chat_id,
        user_id=current_user.id,
        cursor=cursor,
        limit=limit,
    )

    message_list = []
    for msg in reversed(messages):
        sender_data = None
        if msg.sender_id:
            result = await db.execute(select(User).where(User.id == msg.sender_id))
            sender = result.scalar_one_or_none()
            if sender:
                sender_data = {
                    "id": sender.id,
                    "full_name": sender.full_name,
                    "avatar_url": sender.avatar_url,
                }
        message_list.append(MessageResponse(
            id=msg.id,
            chat_id=msg.chat_id,
            sender_id=msg.sender_id,
            type=msg.type,
            content=msg.content,
            media_url=msg.media_url,
            reply_to_id=msg.reply_to_id,
            is_read=msg.is_read,
            is_deleted=msg.is_deleted,
            created_at=msg.created_at,
            sender=sender_data,
        ))

    return MessageListResponse(
        messages=message_list,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.post("/{chat_id}/messages", response_model=MessageResponse)
async def send_message(
    chat_id: str,
    data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    message = await service.create_message(
        chat_id=chat_id,
        sender_id=current_user.id,
        message_data=data,
    )
    return MessageResponse(
        id=message.id,
        chat_id=message.chat_id,
        sender_id=message.sender_id,
        type=message.type,
        content=message.content,
        media_url=message.media_url,
        reply_to_id=message.reply_to_id,
        is_read=message.is_read,
        is_deleted=message.is_deleted,
        created_at=message.created_at,
        sender={
            "id": current_user.id,
            "full_name": current_user.full_name,
            "avatar_url": current_user.avatar_url,
        },
    )


@router.delete("/{chat_id}/messages/{msg_id}")
async def delete_message(
    chat_id: str,
    msg_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    deleted = await service.delete_message(msg_id, current_user.id)
    if not deleted:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Message deleted successfully"}


@router.post("/{chat_id}/messages/read")
async def mark_messages_read(
    chat_id: str,
    data: ReadReceiptRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = MessageService(db)
    await service.mark_as_read(
        chat_id=chat_id,
        user_id=current_user.id,
        message_ids=data.message_ids,
    )
    return {"message": "Messages marked as read"}
