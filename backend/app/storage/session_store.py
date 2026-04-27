from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


class SessionStore:
    async def get(self, sid: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    async def set(self, sid: str, data: Dict[str, Any], ttl_seconds: int) -> None:
        raise NotImplementedError

    async def delete(self, sid: str) -> None:
        raise NotImplementedError


@dataclass
class _MemItem:
    data: Dict[str, Any]
    expires_at: float


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._items: dict[str, _MemItem] = {}

    def _gc(self) -> None:
        now = time.time()
        expired = [k for k, v in self._items.items() if v.expires_at <= now]
        for k in expired:
            self._items.pop(k, None)

    async def get(self, sid: str) -> Optional[Dict[str, Any]]:
        self._gc()
        item = self._items.get(sid)
        if not item:
            return None
        return item.data

    async def set(self, sid: str, data: Dict[str, Any], ttl_seconds: int) -> None:
        self._items[sid] = _MemItem(data=data, expires_at=time.time() + ttl_seconds)

    async def delete(self, sid: str) -> None:
        self._items.pop(sid, None)


class RedisSessionStore(SessionStore):
    def __init__(self, redis) -> None:
        self.redis = redis

    def _key(self, sid: str) -> str:
        return f"session:{sid}"

    async def get(self, sid: str) -> Optional[Dict[str, Any]]:
        raw = await self.redis.get(self._key(sid))
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def set(self, sid: str, data: Dict[str, Any], ttl_seconds: int) -> None:
        await self.redis.set(self._key(sid), json.dumps(data), ex=ttl_seconds)

    async def delete(self, sid: str) -> None:
        await self.redis.delete(self._key(sid))
