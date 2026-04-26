from fastapi import WebSocket
from typing import Dict, Set, Optional
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # user_id -> set of websocket connections
        self._active_connections: Dict[str, Set[WebSocket]] = {}
        # websocket -> user_id mapping
        self._socket_user: Dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        async with self._lock:
            if user_id not in self._active_connections:
                self._active_connections[user_id] = set()
            self._active_connections[user_id].add(websocket)
            self._socket_user[websocket] = user_id
        logger.info(f"User {user_id} connected. Total connections: {self.total_connections}")

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            user_id = self._socket_user.pop(websocket, None)
            if user_id and user_id in self._active_connections:
                self._active_connections[user_id].discard(websocket)
                if not self._active_connections[user_id]:
                    del self._active_connections[user_id]
        if user_id:
            logger.info(f"User {user_id} disconnected. Total connections: {self.total_connections}")

    @property
    def total_connections(self) -> int:
        return sum(len(sockets) for sockets in self._active_connections.values())

    def is_online(self, user_id: str) -> bool:
        return user_id in self._active_connections and bool(self._active_connections[user_id])

    def get_online_users(self) -> Set[str]:
        return set(self._active_connections.keys())

    async def send_to_user(self, user_id: str, event: str, data: dict):
        if user_id not in self._active_connections:
            return
        message = json.dumps({"event": event, "data": data})
        dead_sockets = set()
        for websocket in self._active_connections[user_id].copy():
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")
                dead_sockets.add(websocket)
        # Clean up dead connections
        for ws in dead_sockets:
            await self.disconnect(ws)

    async def broadcast_to_users(self, user_ids: list, event: str, data: dict):
        tasks = [self.send_to_user(uid, event, data) for uid in user_ids]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_message_event(self, chat_member_ids: list, message_data: dict):
        await self.broadcast_to_users(chat_member_ids, "message.new", message_data)

    async def send_read_event(self, user_id: str, chat_id: str, message_ids: list):
        await self.send_to_user(user_id, "message.read", {
            "chat_id": chat_id,
            "message_ids": message_ids,
        })

    async def send_typing_event(self, user_ids: list, sender_id: str, chat_id: str, is_typing: bool):
        await self.broadcast_to_users(user_ids, "user.typing", {
            "user_id": sender_id,
            "chat_id": chat_id,
            "is_typing": is_typing,
        })

    async def send_online_event(self, user_ids: list, target_user_id: str, is_online: bool):
        await self.broadcast_to_users(user_ids, "user.online", {
            "user_id": target_user_id,
            "is_online": is_online,
        })

    async def send_call_event(self, user_id: str, call_data: dict):
        await self.send_to_user(user_id, "call.incoming", call_data)


manager = ConnectionManager()
