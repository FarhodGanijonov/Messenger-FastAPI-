from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from typing import List
from app.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.chat import Chat, ChatMember
from app.models.message import Message
from app.schemas.chat import ChatCreate, ChatResponse, ChatDetailResponse
import uuid

router = APIRouter(prefix="/api/chats", tags=["Chats"])


@router.get("", response_model=List[dict])
async def get_chats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get all chats for the user
    result = await db.execute(
        select(ChatMember).where(ChatMember.user_id == current_user.id)
    )
    memberships = result.scalars().all()
    chat_ids = [m.chat_id for m in memberships]

    if not chat_ids:
        return []

    chats_result = await db.execute(
        select(Chat).where(Chat.id.in_(chat_ids), Chat.is_active == True)
    )
    chats = chats_result.scalars().all()

    response = []
    for chat in chats:
        # Get member count
        count_result = await db.execute(
            select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat.id)
        )
        member_count = count_result.scalar()

        # Get last message
        last_msg_result = await db.execute(
            select(Message)
            .where(Message.chat_id == chat.id, Message.is_deleted == False)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        last_message = last_msg_result.scalar_one_or_none()

        # Get unread count
        membership = next((m for m in memberships if m.chat_id == chat.id), None)
        unread_result = await db.execute(
            select(func.count(Message.id)).where(
                and_(
                    Message.chat_id == chat.id,
                    Message.sender_id != current_user.id,
                    Message.is_read == False,
                    Message.is_deleted == False,
                )
            )
        )
        unread_count = unread_result.scalar()

        # For direct chats, get the other user's name
        chat_name = chat.name
        chat_avatar = chat.avatar_url
        if chat.type == "direct":
            other_member_result = await db.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == chat.id,
                    ChatMember.user_id != current_user.id,
                )
            )
            other_member = other_member_result.scalar_one_or_none()
            if other_member:
                other_user_result = await db.execute(
                    select(User).where(User.id == other_member.user_id)
                )
                other_user = other_user_result.scalar_one_or_none()
                if other_user:
                    chat_name = other_user.full_name or other_user.phone
                    chat_avatar = other_user.avatar_url

        response.append({
            "id": chat.id,
            "type": chat.type,
            "name": chat_name,
            "avatar_url": chat_avatar,
            "member_count": member_count,
            "unread_count": unread_count,
            "created_at": chat.created_at.isoformat(),
            "last_message": {
                "id": last_message.id,
                "type": last_message.type,
                "content": last_message.content,
                "sender_id": last_message.sender_id,
                "created_at": last_message.created_at.isoformat(),
            } if last_message else None,
        })

    return sorted(response, key=lambda x: x["last_message"]["created_at"] if x["last_message"] else x["created_at"], reverse=True)


@router.post("", response_model=dict)
async def create_chat(
    data: ChatCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.type == "direct":
        if len(data.member_ids) != 1:
            raise HTTPException(status_code=400, detail="Direct chat requires exactly 1 other member")

        other_id = data.member_ids[0]
        # Check if direct chat already exists
        existing = await db.execute(
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(
                Chat.type == "direct",
                ChatMember.user_id == current_user.id,
            )
        )
        existing_chats = existing.scalars().all()

        for ec in existing_chats:
            other_result = await db.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == ec.id,
                    ChatMember.user_id == other_id,
                )
            )
            if other_result.scalar_one_or_none():
                return {"id": ec.id, "type": ec.type, "created_at": ec.created_at.isoformat()}

    chat_id = str(uuid.uuid4())
    chat = Chat(
        id=chat_id,
        type=data.type,
        name=data.name,
        created_by=current_user.id,
    )
    db.add(chat)
    await db.flush()

    # Add creator as admin member
    creator_member = ChatMember(
        id=str(uuid.uuid4()),
        chat_id=chat_id,
        user_id=current_user.id,
        role="admin",
    )
    db.add(creator_member)

    # Add other members
    for member_id in data.member_ids:
        result = await db.execute(select(User).where(User.id == member_id, User.is_active == True))
        user = result.scalar_one_or_none()
        if user:
            member = ChatMember(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                user_id=member_id,
                role="member",
            )
            db.add(member)

    await db.flush()
    return {"id": chat.id, "type": chat.type, "name": chat.name, "created_at": chat.created_at.isoformat()}


@router.get("/{chat_id}", response_model=dict)
async def get_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member_result = await db.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == current_user.id,
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this chat")

    chat_result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    members_result = await db.execute(
        select(ChatMember, User)
        .join(User, User.id == ChatMember.user_id)
        .where(ChatMember.chat_id == chat_id)
    )
    members = [
        {
            "id": m.id,
            "user_id": u.id,
            "full_name": u.full_name,
            "avatar_url": u.avatar_url,
            "role": m.role,
            "joined_at": m.joined_at.isoformat(),
        }
        for m, u in members_result.fetchall()
    ]

    return {
        "id": chat.id,
        "type": chat.type,
        "name": chat.name,
        "avatar_url": chat.avatar_url,
        "description": chat.description,
        "created_by": chat.created_by,
        "created_at": chat.created_at.isoformat(),
        "members": members,
    }


@router.delete("/{chat_id}")
async def delete_chat(
    chat_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    member_result = await db.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id,
            ChatMember.user_id == current_user.id,
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this chat")

    if member.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete chat")

    chat_result = await db.execute(select(Chat).where(Chat.id == chat_id))
    chat = chat_result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    chat.is_active = False
    await db.flush()
    return {"message": "Chat deleted successfully"}
