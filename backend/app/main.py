from __future__ import annotations

import contextlib
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.core.session import SessionManager
from app.routers.auth import router as auth_router
from app.routers.ws_chat import router as ws_router
from app.services.agent.agent import Agent
from app.services.agent.llm import LLM
from app.services.agent.tooling_setup import build_registry
from app.services.hrms.hrms_client import HRMSClient
from app.services.speech.tts import TTSService
from app.services.speech.stt import STTService
from app.storage.session_store import InMemorySessionStore, RedisSessionStore


BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
FRONTEND_DIR = (BASE_DIR / "frontend").resolve()
ASSETS_DIR = (FRONTEND_DIR / "assets").resolve()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI):
        http = httpx.AsyncClient(timeout=30, follow_redirects=True)

        if settings.REDIS_URL:
            import redis.asyncio as redis

            r = redis.from_url(settings.REDIS_URL, decode_responses=True)
            store = RedisSessionStore(r)
            app.state.redis = r
        else:
            store = InMemorySessionStore()
            app.state.redis = None

        app.state.settings = settings
        app.state.http = http
        
        # We share the transport for connection pooling, 
        # but HRMSClient will create isolated clients for cookie safety.
        app.state.hrms_transport = httpx.AsyncHTTPTransport(
            verify=True,
            retries=3
        )
        app.state.hrms = HRMSClient(app.state.hrms_transport)
        app.state.session_manager = SessionManager(store)

        tool_registry = build_registry()
        app.state.agent = Agent(llm=LLM(), tools=tool_registry)

        app.state.tts = TTSService()
        app.state.stt = STTService(http)

        yield

        await http.aclose()
        if app.state.redis is not None:
            await app.state.redis.close()

    app.router.lifespan_context = lifespan

    # Frontend static
    if ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

    app.include_router(auth_router)
    app.include_router(ws_router)

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/login")

    @app.get("/login", include_in_schema=False)
    def login_page():
        with open(FRONTEND_DIR / "login.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())

    @app.get("/chat", include_in_schema=False)
    def chat_page():
        with open(FRONTEND_DIR / "chat.html", "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())

    return app


app = create_app()
