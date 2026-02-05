from fastapi import APIRouter, Form, HTTPException, Response, Cookie
from app.auth.hrms import HRMSClient
from app.auth.session import create_session
from fastapi.responses import JSONResponse
from app.auth.session import SESSION_STORE


router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/login")
def login(
    response: Response,
    userName: str = Form(...),
    password: str = Form(...),
    registrationToken: str = Form(...)
):
    client = HRMSClient()

    auth_response = client.login(userName, password, registrationToken)

    session_id = create_session(auth_response)

    response.set_cookie(
        key="chatbot_session",
        value=session_id,
        httponly=True
    )

    return {
    "message": "Login successful",
    "session_id": session_id,   # 👈 ADD THIS
    "user": auth_response["json"]
    }



@router.post("/logout")
def logout(
    response: Response,
    chatbot_session: str | None = Cookie(None)
):
    if chatbot_session and chatbot_session in SESSION_STORE:
        del SESSION_STORE[chatbot_session]

    response.delete_cookie("chatbot_session")

    return {"message": "Logged out"}