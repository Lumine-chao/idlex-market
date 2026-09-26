"""WebSocket 长连接管理器：用户连接注册、跨端广播、未读推送（单进程实现）"""
import asyncio
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # user_id -> set(WebSocket)
        self._connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self._connections.setdefault(user_id, set()).add(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        conns = self._connections.get(user_id)
        if conns and ws in conns:
            conns.discard(ws)
            if not conns:
                self._connections.pop(user_id, None)

    def is_online(self, user_id: int) -> bool:
        return bool(self._connections.get(user_id))

    async def send_to_user(self, user_id: int, envelope: dict):
        conns = self._connections.get(user_id)
        if not conns:
            return False
        dead = []
        for ws in list(conns):
            try:
                await ws.send_json(envelope)
            except Exception:
                dead.append(ws)
        for ws in dead:
            conns.discard(ws)
        return True

    async def broadcast_unread(self, user_id: int, unread_total: int):
        await self.send_to_user(user_id, {
            "type": "UNREAD_TOTAL", "payload": {"total": unread_total}})


manager = ConnectionManager()