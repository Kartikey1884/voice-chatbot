"""
Text chat WebSocket endpoint
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any
import os

from app.services.chatbot import ChatBot
from app.core.logging import logger


async def text_chat_websocket(websocket: WebSocket, chatbot: ChatBot, active_sessions: Dict[str, Dict[str, Any]], get_or_create_session):
    """
    WebSocket endpoint for TEXT-ONLY chat
    Handles streaming text responses from LLM
    SHARES SESSION with voice mode
    """
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "text":
                # Initialize or get existing session
                if not session_id:
                    session_id = data.get("session_id", os.urandom(8).hex())
                
                session_info = get_or_create_session(session_id)
                session_info["modes_used"].add("text")
                
                text = data.get("text", "").strip()
                if not text:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty message"
                    })
                    continue
                
                # Stream chatbot response using SHARED session
                await websocket.send_json({"type": "status", "message": "Thinking..."})
                
                full_response = ""
                async for chunk in chatbot.stream_response(text, session_id):
                    full_response += chunk
                    await websocket.send_json({
                        "type": "text_chunk",
                        "text": chunk
                    })
                
                session_info["message_count"] += 1
                
                # Send completion
                await websocket.send_json({
                    "type": "text_complete",
                    "text": full_response
                })
            
            elif data["type"] == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        logger.info(f"📱 Text chat disconnected - Session: {session_id}")
    except Exception as e:
        logger.error(f" Text chat error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
