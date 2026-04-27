from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, WebSocket

from app.config import settings
from app.core.session import SessionManager


async def get_session_from_request(request: Request, sm: SessionManager) -> Dict[str, Any]:
    cookie_val = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if not cookie_val:
        raise HTTPException(status_code=401, detail="Not authenticated")
    sid = sm.decode_cookie(cookie_val)
    if not sid:
        raise HTTPException(status_code=401, detail="Invalid session")
    data = await sm.get(sid)
    if not data:
        raise HTTPException(status_code=401, detail="Session expired")
    request.state.sid = sid
    return data


async def get_session_from_ws(ws: WebSocket, sm: SessionManager) -> tuple[str, Dict[str, Any]]:
    cookie_val = ws.cookies.get(settings.SESSION_COOKIE_NAME)
    if not cookie_val:
        await ws.close(code=4401)
        raise RuntimeError("No session cookie")
    sid = sm.decode_cookie(cookie_val)
    if not sid:
        await ws.close(code=4401)
        raise RuntimeError("Invalid session")
    data = await sm.get(sid)
    if not data:
        await ws.close(code=4401)
        raise RuntimeError("Session expired")
    return sid, data
