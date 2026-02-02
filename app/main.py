"""
app/main.py
───────────
FastAPI entry point.

• Serves the single-page frontend from app/templates/index.html
• Mounts static assets from app/static/
• Exposes two WebSocket endpoints that share one session store
• Provides /health and /session/* management endpoints
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from datetime import datetime
from typing import Dict, Any

from app.core.config import settings
from app.core.logging import logger
from app.services.chatbot import ChatBot
from app.api.chat import text_chat_websocket
from app.api.voice import voice_chat_websocket

# ── app & middleware ──────────────────────────────────────────
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

# ── singletons ────────────────────────────────────────────────
chatbot = ChatBot()

# Shared session metadata (separate from chatbot.sessions which holds message history).
# Both text and voice WebSockets read/write the SAME entry so the user can
# switch modes mid-conversation without losing context.
active_sessions: Dict[str, Dict[str, Any]] = {}


def get_or_create_session(session_id: str) -> Dict[str, Any]:
    """Return existing session metadata or create a fresh one."""
    if session_id not in active_sessions:
        active_sessions[session_id] = {
            "created_at":    datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0,
            "modes_used":    set(),
        }
        logger.info("✨ New session: %s", session_id)
    else:
        active_sessions[session_id]["last_activity"] = datetime.now()
    return active_sessions[session_id]


# ── WebSocket routes ──────────────────────────────────────────

@app.websocket("/ws/text")
async def text_ws(websocket: WebSocket):
    await text_chat_websocket(websocket, chatbot, active_sessions, get_or_create_session)


@app.websocket("/ws/voice")
async def voice_ws(websocket: WebSocket):
    await voice_chat_websocket(websocket, chatbot, active_sessions, get_or_create_session)


# ── REST helpers ──────────────────────────────────────────────

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    if session_id in active_sessions:
        s = active_sessions[session_id]
        return {
            "session_id":    session_id,
            "created_at":    s["created_at"].isoformat(),
            "last_activity": s["last_activity"].isoformat(),
            "message_count": s["message_count"],
            "modes_used":    list(s["modes_used"]),
        }
    return {"error": "Session not found"}


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    if session_id in active_sessions:
        del active_sessions[session_id]
        chatbot.clear_session(session_id)
        return {"message": "Session cleared", "session_id": session_id}
    return {"error": "Session not found"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "endpoints": {
            "text_chat":  "/ws/text",
            "voice_chat": "/ws/voice",
        },
        "model": settings.LLM_MODEL,
        "tts":   "elevenlabs",
        "stt":   "edge-stt (browser)",
        "features": {
            "shared_sessions":          True,
            "voice_auto_greeting":      True,
            "voice_idle_follow_up":     "12 seconds after bot finishes",
            "voice_idle_goodbye":       "20 seconds after follow-up",
            "barge_in_interrupt":       True,
            "cross_mode_context":       True,
        },
        "active_sessions": len(active_sessions),
    }


# ── favicon & SPA catch-all ───────────────────────────────────

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    path = settings.STATIC_DIR / "favicon.ico"
    return FileResponse(str(path)) if path.exists() else Response(status_code=204)


@app.get("/")
async def root():
    return FileResponse(str(settings.TEMPLATES_DIR / "index.html"))


# ── CLI entry point ───────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    if not settings.validate():
        logger.warning("⚠️  Some required settings are missing — check your .env file.")

    logger.info("🚀 Starting server…")
    logger.info("📝 Text  → ws://localhost:%d/ws/text", settings.PORT)
    logger.info("🎤 Voice → ws://localhost:%d/ws/voice", settings.PORT)
    logger.info("🔄 Shared sessions enabled | 🏃 Idle timers: 12 s follow-up / 20 s goodbye")

    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
