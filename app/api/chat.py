"""
app/api/chat.py
───────────────
WebSocket handler for TEXT chat.

Protocol (all frames are JSON):
  Client → Server:   { "type": "text",  "text": "…",  "session_id": "…" }
                     { "type": "ping" }

  Server → Client:   { "type": "status",        "message": "…" }
                     { "type": "text_chunk",     "text": "…" }        ← streaming token
                     { "type": "text_complete",  "text": "…" }        ← full reply (end signal)
                     { "type": "error",          "message": "…" }
                     { "type": "pong" }

Session ID is shared with the voice WebSocket so conversation
history persists when the user switches modes.
"""

import os
from typing import Dict, Any

from fastapi import WebSocket, WebSocketDisconnect

from app.services.chatbot import ChatBot
from app.core.logging import logger


async def text_chat_websocket(
    websocket: WebSocket,
    chatbot: ChatBot,
    active_sessions: Dict[str, Dict[str, Any]],
    get_or_create_session,
):
    await websocket.accept()
    session_id = None

    try:
        while True:
            data = await websocket.receive_json()

            # ── text message ───────────────────────────────────
            if data["type"] == "text":
                # Grab or create the shared session
                if not session_id:
                    session_id = data.get("session_id") or os.urandom(8).hex()

                session_info = get_or_create_session(session_id)
                session_info["modes_used"].add("text")

                text = (data.get("text") or "").strip()
                if not text:
                    await websocket.send_json({"type": "error", "message": "Empty message"})
                    continue

                await websocket.send_json({"type": "status", "message": "Thinking…"})

                # Stream tokens
                full_response = ""
                async for chunk in chatbot.stream_response(text, session_id):
                    full_response += chunk
                    await websocket.send_json({"type": "text_chunk", "text": chunk})

                session_info["message_count"] += 1

                # Signal completion
                await websocket.send_json({"type": "text_complete", "text": full_response})

            # ── keepalive ─────────────────────────────────────
            elif data["type"] == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("📱 Text chat disconnected — session: %s", session_id)
    except Exception as exc:
        logger.error("❌ Text chat error: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
