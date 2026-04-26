from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, func
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import datetime
from app.models.message import Message, MediaFile
from app.models.chat import Chat, ChatMember
from app.models.user import User
from app.schemas.message import MessageCreate
from app.core.websocket_manager import manager
import uuid


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_chat_messages(
        self,
        chat_id: str,
        user_id: str,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> Tuple[List[Message], Optional[str], bool]:
        # Verify user is member
        member_result = await self.db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id,
            )
        )
        if not member_result.scalar_one_or_none():
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not a member of this chat")

        query = (
            select(Message)
            .where(Message.chat_id == chat_id, Message.is_deleted == False)
            .order_by(Message.created_at.desc())
            .limit(limit + 1)
        )

        if cursor:
            # cursor is a message id; get messages older than that
            cursor_result = await self.db.execute(
                select(Message.created_at).where(Message.id == cursor)
            )
            cursor_time = cursor_result.scalar_one_or_none()
            if cursor_time:
                query = query.where(Message.created_at < cursor_time)

        result = await self.db.execute(query)
        messages = result.scalars().all()

        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        next_cursor = messages[-1].id if has_more and messages else None

        return list(messages), next_cursor, has_more

    async def create_message(
        self,
        chat_id: str,
        sender_id: str,
        message_data: MessageCreate,
    ) -> Message:
        # Verify membership
        member_result = await self.db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == sender_id,
            )
        )
        if not member_result.scalar_one_or_none():
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not a member of this chat")

        # Get media URL if media_id provided
        media_url = None
        if message_data.media_id:
            media_result = await self.db.execute(
                select(MediaFile).where(MediaFile.id == message_data.media_id)
            )
            media = media_result.scalar_one_or_none()
            if media:
                media_url = media.url

        message = Message(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            sender_id=sender_id,
            type=message_data.type,
            content=message_data.content,
            media_id=message_data.media_id,
            media_url=media_url,
            reply_to_id=message_data.reply_to_id,
        )
        self.db.add(message)
        await self.db.flush()

        # Notify chat members
        members_result = await self.db.execute(
            select(ChatMember.user_id).where(ChatMember.chat_id == chat_id)
        )
        member_ids = [row[0] for row in members_result.fetchall()]

        sender_result = await self.db.execute(select(User).where(User.id == sender_id))
        sender = sender_result.scalar_one_or_none()

        await manager.send_message_event(
            member_ids,
            {
                "id": message.id,
                "chat_id": chat_id,
                "sender_id": sender_id,
                "sender_name": sender.full_name if sender else None,
                "type": message.type,
                "content": message.content,
                "media_url": message.media_url,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            },
        )

        return message

    async def delete_message(self, message_id: str, user_id: str) -> bool:
        result = await self.db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            return False

        if message.sender_id != user_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Cannot delete another user's message")

        message.is_deleted = True
        message.content = None
        await self.db.flush()
        return True

    async def mark_as_read(self, chat_id: str, user_id: str, message_ids: Optional[List[str]] = None):
        if message_ids:
            # Faqat berilgan xabarlarni o'qilgan deb belgilash
            result = await self.db.execute(
                select(Message).where(
                    Message.id.in_(message_ids),
                    Message.chat_id == chat_id,
                    Message.sender_id != user_id,
                )
            )
            messages = result.scalars().all()
            sender_ids = set()
            for msg in messages:
                msg.is_read = True
                if msg.sender_id:
                    sender_ids.add(msg.sender_id)
        else:
            # Barcha xabarlarni o'qilgan deb belgilash
            result = await self.db.execute(
                select(Message).where(
                    Message.chat_id == chat_id,
                    Message.sender_id != user_id,
                    Message.is_read == False,
                )
            )
            messages = result.scalars().all()
            sender_ids = set()
            message_ids = []
            for msg in messages:
                msg.is_read = True
                message_ids.append(msg.id)
                if msg.sender_id:
                    sender_ids.add(msg.sender_id)

        # last_read_at yangilash
        await self.db.execute(
            update(ChatMember)
            .where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
            .values(last_read_at=datetime.utcnow())
        )
        await self.db.flush()

        # Har bir sender ga read receipt yuborish
        for sender_id in sender_ids:
            await manager.send_to_user(sender_id, "message.read", {
                "chat_id": chat_id,
                "message_ids": message_ids,
                "read_by": user_id,
            })