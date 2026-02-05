"""
<<<<<<< Updated upstream
Text chat WebSocket endpoint
"""

=======
app/api/chat.py
───────────────
WebSocket handler for TEXT chat.
Uses HRMS login session as source of truth.
"""

from typing import Dict, Any
>>>>>>> Stashed changes
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any
import os

from app.services.chatbot import ChatBot
from app.core.logging import logger
from app.auth.session import get_session


<<<<<<< Updated upstream
async def text_chat_websocket(websocket: WebSocket, chatbot: ChatBot, active_sessions: Dict[str, Dict[str, Any]], get_or_create_session):
    """
    WebSocket endpoint for TEXT-ONLY chat
    Handles streaming text responses from LLM
    SHARES SESSION with voice mode
    """
=======
async def text_chat_websocket(
    websocket: WebSocket,
    chatbot: ChatBot,
    active_sessions: Dict[str, Dict[str, Any]],  # kept for compatibility
    get_or_create_session,                      # kept for compatibility
):
>>>>>>> Stashed changes
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
<<<<<<< Updated upstream
            
            if data["type"] == "text":
                # Initialize or get existing session
                if not session_id:
                    session_id = data.get("session_id", os.urandom(8).hex())
                
                session_info = get_or_create_session(session_id)
                session_info["modes_used"].add("text")
                
                text = data.get("text", "").strip()
=======

            # ── TEXT MESSAGE ─────────────────────────────────────
            if data["type"] == "text":

                session_id = data.get("session_id")
                if not session_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Session expired. Please login again."
                    })
                    continue

                logger.info("✨ New session: %s", session_id)

                # 🔐 Fetch real HRMS session
                session_info = get_session(session_id)

                if not session_info or "hrms" not in session_info:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Please login first"
                    })
                    continue

                text = (data.get("text") or "").strip()
>>>>>>> Stashed changes
                if not text:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty message"
                    })
                    continue
<<<<<<< Updated upstream
                
                # Stream chatbot response using SHARED session
                await websocket.send_json({"type": "status", "message": "Thinking..."})
                
=======

                # ── Normalize HRMS login data ───────────────────
                raw = session_info["hrms"]["user"]["DATA"]
                cookies = session_info["hrms"]["cookies"]

                chat_user = {
                    "id": raw["id"],
                    "name": raw["name"],
                    "email": raw["email"],
                    "department": raw["department"]["name"],
                    "designation": raw["designation"]["name"],
                    "company": raw["company"]["name"],
                    "location": raw["location"]["name"],
                    "reportsTo": raw.get("reportsTo", {}).get("name", "N/A"),
                    "status": raw["status"]["name"],
                    "doj": raw["doj"]
                }

                # Inject user context once per session
                chatbot.set_user_context(session_id, chat_user)

                await websocket.send_json({
                    "type": "status",
                    "message": "Thinking…"
                })

                # ── Stream response (COOKIES, NOT TOKEN) ─────────
>>>>>>> Stashed changes
                full_response = ""
                async for chunk in chatbot.stream_response(
                    message=text,
                    session_id=session_id,
                    cookies=cookies
                ):
                    full_response += chunk
                    await websocket.send_json({
                        "type": "text_chunk",
                        "text": chunk
                    })
<<<<<<< Updated upstream
                
                session_info["message_count"] += 1
                
                # Send completion
=======

>>>>>>> Stashed changes
                await websocket.send_json({
                    "type": "text_complete",
                    "text": full_response
                })
<<<<<<< Updated upstream
            
=======

            # ── KEEPALIVE ───────────────────────────────────────
>>>>>>> Stashed changes
            elif data["type"] == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
<<<<<<< Updated upstream
        logger.info(f"📱 Text chat disconnected - Session: {session_id}")
    except Exception as e:
        logger.error(f" Text chat error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
=======
        logger.info("📱 Text chat disconnected — session: %s", session_id)

    except Exception:
        logger.exception("❌ Text chat error")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Internal server error"
            })
        except Exception:
            pass
>>>>>>> Stashed changes
