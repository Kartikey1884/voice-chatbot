from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.tool_router import admin_chat_once

router = APIRouter()

@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await ws.accept()
    try:
        token = ws.query_params.get("token")
        # SessionMiddleware cookies are available via ws.cookies, BUT not session itself.
        # So we validate token by calling a lightweight HTTP endpoint before connecting and sending token here.
        # We'll re-check by asking client to send user + a token confirmation payload.
        # (Cleanest approach without decoding signed session cookie server-side.)
        await ws.send_json({"type": "ready", "message": "connected"})

        while True:
            msg = await ws.receive_json()

            if msg.get("type") == "auth":
                # client sends {type:"auth", token, user, hrmsCookiesPresent:true/false}
                ws.state.user = msg.get("user")
                ws.state.token = msg.get("token")
                ws.state.hrms = msg.get("hrmsCookies")
                if not ws.state.user or ws.state.token != token:
                    await ws.send_json({"type": "error", "message": "Auth failed"})
                    await ws.close()
                    return
                await ws.send_json({"type": "authed", "message": "ok"})
                continue

            if msg.get("type") == "user":
                user = getattr(ws.state, "user", None)
                hrms_cookies = getattr(ws.state, "hrms", None) or {}
                if not user:
                    await ws.send_json({"type": "error", "message": "Not authenticated"})
                    continue

                # Admin-only for this phase
                if (user.get("userType") or "").lower() != "admin":
                    await ws.send_json({"type": "assistant", "text": "Admin tools are enabled only for Admin users."})
                    continue

                text = msg.get("text", "")
                reply = await admin_chat_once(user=user, hrms_cookies=hrms_cookies, user_text=text)
                await ws.send_json({"type": "assistant", "text": reply})

    except WebSocketDisconnect:
        return
