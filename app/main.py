"""
FastAPI application entry point
Separate WebSocket endpoints for voice and text chat
WITH SHARED SESSION SUPPORT - conversation history persists across mode switches
"""

from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
<<<<<<< Updated upstream
from fastapi.responses import FileResponse, Response
import os
from pathlib import Path
=======
from fastapi.responses import FileResponse, Response, RedirectResponse
>>>>>>> Stashed changes
from datetime import datetime
from typing import Dict, Any

from app.core.config import settings
from app.core.logging import logger
from app.services.chatbot import ChatBot
from app.api.chat import text_chat_websocket
from app.api.voice import voice_chat_websocket
from app.auth.routes import router as auth_router
from app.auth.session import get_session as get_auth_session



# Initialize FastAPI app
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
app.include_router(auth_router)

# Initialize chatbot
chatbot = ChatBot()

# 🔄 SHARED SESSION STORAGE
# Stores conversation history across text and voice modes
active_sessions: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: str) -> Dict[str, Any]:
    """Get existing session or create new one"""
    if session_id not in active_sessions:
        active_sessions[session_id] = {
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0,
            "modes_used": set()
        }
        logger.info(f"✨ Created new session: {session_id}")
    else:
        active_sessions[session_id]["last_activity"] = datetime.now()
        logger.info(f"📝 Using existing session: {session_id} (messages: {active_sessions[session_id]['message_count']})")
    
    return active_sessions[session_id]

def get_user_context(session_id: str) -> dict:
    auth_session = get_auth_session(session_id)

    if not auth_session:
        return {}

    return auth_session["hrms"]["user"]


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    favicon_path = settings.STATIC_DIR / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(str(favicon_path))
    return Response(status_code=204)


@app.websocket("/ws/text")
async def text_chat_ws(websocket: WebSocket):
    """Text chat WebSocket endpoint"""
    await text_chat_websocket(websocket, chatbot, active_sessions, get_or_create_session)


@app.websocket("/ws/voice")
async def voice_chat_ws(websocket: WebSocket):
    """Voice chat WebSocket endpoint"""
    await voice_chat_websocket(websocket, chatbot, active_sessions, get_or_create_session)


@app.get("/session/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a session"""
    if session_id in active_sessions:
        session = active_sessions[session_id]
        return {
            "session_id": session_id,
            "created_at": session["created_at"].isoformat(),
            "last_activity": session["last_activity"].isoformat(),
            "message_count": session["message_count"],
            "modes_used": list(session["modes_used"])
        }
    return {"error": "Session not found"}


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific session"""
    if session_id in active_sessions:
        del active_sessions[session_id]
        # Also clear from chatbot
        if hasattr(chatbot, 'sessions') and session_id in chatbot.sessions:
            del chatbot.sessions[session_id]
        return {"message": "Session cleared", "session_id": session_id}
    return {"error": "Session not found"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "endpoints": {
            "text_chat": "/ws/text",
            "voice_chat": "/ws/voice",
            "session_info": "/session/{session_id}",
            "clear_session": "/session/{session_id} (DELETE)"
        },
        "model": settings.LLM_MODEL,
        "tts": "edge-tts",
        "stt": "faster-whisper",
        "features": {
            "shared_sessions": True,
            "voice_auto_greeting": True,
            "voice_idle_timeout": "20 seconds (after bot finishes)",
            "voice_follow_up": "8 seconds (after bot finishes)",
            "timer_pauses_during_bot_processing": True,
            "cross_mode_context": True
        },
        "active_sessions": len(active_sessions)
    }


@app.get("/")
async def root():
    return FileResponse(str(settings.TEMPLATES_DIR / "login.html"))


<<<<<<< Updated upstream
# For uvicorn command line usage:
# uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
=======
@app.get("/chat")
async def chat_page(request: Request):
    session_id = request.cookies.get("chatbot_session")

    if not session_id or not get_auth_session(session_id):
        return RedirectResponse("/")

    return FileResponse(str(settings.TEMPLATES_DIR / "index.html"))

# ── CLI entry point ───────────────────────────────────────────
>>>>>>> Stashed changes

if __name__ == "__main__":
    import uvicorn
    
    # Validate settings
    if not settings.validate():
        logger.warning("⚠️ Some required settings are missing. Check your .env file.")
    
    logger.info("🚀 Starting server...")
    logger.info(f"📝 Text chat endpoint: ws://localhost:{settings.PORT}/ws/text")
    logger.info(f"🎤 Voice chat endpoint: ws://localhost:{settings.PORT}/ws/voice")
    logger.info("🔄 Shared sessions: Text & Voice modes share conversation history")
    logger.info("⏱️  Voice features: Auto-greeting, 8s follow-up, 20s timeout")
    logger.info("⏸️  Timer PAUSES while bot is processing/speaking")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
