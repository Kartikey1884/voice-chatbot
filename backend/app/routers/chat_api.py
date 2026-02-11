from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.tool_router import admin_chat_once

router = APIRouter(prefix="/api", tags=["chat"])


class ChatBody(BaseModel):
    text: str = Field(min_length=1)


@router.post("/chat")
async def chat(body: ChatBody, request: Request):
    """
    Single-turn chat endpoint.
    Uses session user + HRMS cookies from login.
    Admin tools only for now.
    """
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    hrms_cookies = request.session.get("hrms_cookies") or {}

    role = (user.get("userType") or "").lower()
    if role == "admin":
        reply = await admin_chat_once(user=user, hrms_cookies=hrms_cookies, user_text=body.text)
        return {"ok": True, "reply": reply}

    return {"ok": True, "reply": "Employee tools are not enabled yet. Please log in as Admin to test leave APIs."}
