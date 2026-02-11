from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.config import SESSION_SECRET
from app.routers.auth import router as auth_router
from app.routers.chat_api import router as chat_api_router


app = FastAPI()

# Session cookie (HttpOnly). In production: add HTTPS + secure=True + proper same_site.
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="sid",
    https_only=False,     # set True in prod behind HTTPS
    same_site="lax",
)

# Serve frontend as static
app.mount("/assets", StaticFiles(directory="../frontend/assets"), name="assets")

app.include_router(auth_router)
app.include_router(chat_api_router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/login")

@app.get("/login", include_in_schema=False)
def login_page():
    with open("../frontend/login.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/chat", include_in_schema=False)
def chat_page():
    with open("../frontend/chat.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())