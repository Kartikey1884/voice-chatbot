from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.config import settings
from app.storage.session_store import SessionStore


class SessionManager:
    """Cookie carries a signed token. Actual session data lives in store.

    This makes WebSocket auth easy: we can decode cookie and load session.
    """

    def __init__(self, store: SessionStore) -> None:
        self.store = store
        self.serializer = URLSafeTimedSerializer(settings.SESSION_SECRET, salt="hrms-chatbot")

    def encode_cookie(self, sid: str) -> str:
        return self.serializer.dumps({"sid": sid})

    def decode_cookie(self, cookie_val: str) -> Optional[str]:
        try:
            data = self.serializer.loads(cookie_val, max_age=settings.SESSION_TTL_SECONDS)
            sid = (data or {}).get("sid")
            return sid if isinstance(sid, str) and sid else None
        except BadSignature:
            return None

    async def create(self, payload: Dict[str, Any]) -> str:
        sid = uuid.uuid4().hex
        await self.store.set(sid, payload, ttl_seconds=settings.SESSION_TTL_SECONDS)
        return sid

    async def get(self, sid: str) -> Optional[Dict[str, Any]]:
        return await self.store.get(sid)

    async def update(self, sid: str, payload: Dict[str, Any]) -> None:
        await self.store.set(sid, payload, ttl_seconds=settings.SESSION_TTL_SECONDS)

    async def destroy(self, sid: str) -> None:
        await self.store.delete(sid)
