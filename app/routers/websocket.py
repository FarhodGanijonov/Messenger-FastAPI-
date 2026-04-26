from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from sqlalchemy import select, update
from datetime import datetime
from app.core.security import verify_access_token
from app.core.websocket_manager import manager
from app.database import AsyncSessionLocal
from app.models.user import User
import json
import logging

router = APIRouter(tags=["WebSocket"])
logger = logging.getLogger(__name__)


async def get_user_from_token(token: str):
    user_id = verify_access_token(token)
    if not user_id:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
        return result.scalar_one_or_none()


@router.websocket("/api/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = user.id

    await manager.connect(websocket, user_id)

    # Update last_seen and notify contacts
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(User).where(User.id == user_id).values(last_seen=datetime.utcnow())
        )
        await db.commit()

    await manager.send_to_user(user_id, "connected", {
        "user_id": user_id,
        "online_users": list(manager.get_online_users()),
    })

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                data = json.loads(raw_data)
                event = data.get("event")
                payload = data.get("data", {})

                if event == "user.typing":
                    chat_id = payload.get("chat_id")
                    is_typing = payload.get("is_typing", True)
                    if chat_id:
                        # Get chat members and notify them
                        async with AsyncSessionLocal() as db:
                            from app.models.chat import ChatMember
                            result = await db.execute(
                                select(ChatMember.user_id).where(
                                    ChatMember.chat_id == chat_id,
                                    ChatMember.user_id != user_id,
                                )
                            )
                            member_ids = [row[0] for row in result.fetchall()]
                        await manager.send_typing_event(member_ids, user_id, chat_id, is_typing)

                elif event == "message.read":
                    chat_id = payload.get("chat_id")
                    message_ids = payload.get("message_ids")
                    if chat_id:
                        from app.services.message_service import MessageService
                        async with AsyncSessionLocal() as db:
                            service = MessageService(db)
                            await service.mark_as_read(
                                chat_id=chat_id,
                                user_id=user_id,
                                message_ids=message_ids,
                            )
                            await db.commit()
                            
                elif event == "ping":
                    await websocket.send_text(json.dumps({"event": "pong", "data": {}}))

                else:
                    logger.warning(f"Unknown WebSocket event: {event} from user {user_id}")

            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "event": "error",
                    "data": {"message": "Invalid JSON format"},
                }))

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        # Update last_seen on disconnect
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(User).where(User.id == user_id).values(last_seen=datetime.utcnow())
            )
            await db.commit()
        logger.info(f"User {user_id} disconnected from WebSocket")

    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        await manager.disconnect(websocket)
