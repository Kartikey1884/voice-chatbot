from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.core.deps import get_session_from_request
from app.core.session import SessionManager


router = APIRouter(prefix="/api", tags=["auth"])


class LoginBody(BaseModel):
    userName: str = Field(min_length=1)
    password: str = Field(min_length=1)
    registrationToken: str = Field(min_length=1)


def sm_dep(request: Request) -> SessionManager:
    return request.app.state.session_manager


def hrms_dep(request: Request):
    return request.app.state.hrms


@router.get("/me")
async def me(request: Request, sm: SessionManager = Depends(sm_dep)):
    session = await get_session_from_request(request, sm)
    user = session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": user}


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response, sm: SessionManager = Depends(sm_dep)):
    hrms = hrms_dep(request)
    hrms_json, hrms_cookies, http_status, raw_text, headers = await hrms.authenticate(
        userName=body.userName, password=body.password, registrationToken=body.registrationToken
    )

    if hrms_json is None:
        return {"ok": False, "message": f"HRMS rejected request (HTTP {http_status}).", "debug": raw_text[:300]}

    if hrms_json.get("STATUS") != 1:
        return {"ok": False, "message": hrms_json.get("MESSAGE", "Login failed")}

    user_data = hrms_json.get("DATA") or {}
    user_type_name = ((user_data.get("userType") or {}).get("name") or "").lower()

    user = {
        "id": user_data.get("id"),
        "name": user_data.get("name"),
        "email": user_data.get("email"),
        "phone": user_data.get("phone"),
        "userType": user_type_name,
        "department": (user_data.get("department") or {}).get("name"),
        "designation": (user_data.get("designation") or {}).get("name"),
        "company": (user_data.get("company") or {}).get("name"),
        "location": (user_data.get("location") or {}).get("name"),
        "imageBaseUrl": hrms_json.get("imageBaseUrl"),
        "raw": user_data,
    }

    sid = await sm.create({"user": user, "hrms_cookies": hrms_cookies, "history": []})
    cookie_val = sm.encode_cookie(sid)

    response.set_cookie(
        key=request.app.state.settings.SESSION_COOKIE_NAME,
        value=cookie_val,
        httponly=True,
        samesite="lax",
        secure=False,  # set True behind HTTPS
        max_age=request.app.state.settings.SESSION_TTL_SECONDS,
        path="/",
    )

    return {"ok": True, "message": hrms_json.get("MESSAGE", "Success"), "userType": user_type_name}


@router.post("/logout")
async def logout(request: Request, response: Response, sm: SessionManager = Depends(sm_dep)):
    cookie_val = request.cookies.get(request.app.state.settings.SESSION_COOKIE_NAME)
    if cookie_val:
        sid = sm.decode_cookie(cookie_val)
        if sid:
            await sm.destroy(sid)

    response.delete_cookie(key=request.app.state.settings.SESSION_COOKIE_NAME, path="/")
    return {"ok": True}
