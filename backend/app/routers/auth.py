from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from app.services.hrms.hrms_client import HRMSClient

router = APIRouter(prefix="/api", tags=["auth"])
hrms = HRMSClient()

class LoginBody(BaseModel):
    userName: str = Field(min_length=1)
    password: str = Field(min_length=1)
    registrationToken: str = Field(min_length=1)

@router.get("/me")
async def me(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"user": user}




# ---------------------------------------------------------- LOGIN ----------------------------------------------------------

@router.post("/login")
async def login(body: LoginBody, request: Request):
    hrms_json, hrms_cookies, http_status, raw_text, headers = await hrms.authenticate(
        userName=body.userName,
        password=body.password,
        registrationToken=body.registrationToken,
    )

    # Debug for now
    print("HRMS STATUS:", http_status)
    print("HRMS CONTENT-TYPE:", headers.get("content-type"))
    print("HRMS RAW (first 800):", raw_text[:800])

    # If HRMS didn't return JSON, show a clean message (no crash)
    if hrms_json is None:
        return {
            "ok": False,
            "message": f"HRMS rejected request (HTTP {http_status}).",
            "debug": raw_text[:300],  # remove later
        }

    status = hrms_json.get("STATUS")
    message = hrms_json.get("MESSAGE", "")

    if status != 1:
        return {"ok": False, "message": message or "Login failed"}

    user_data = hrms_json.get("DATA") or {}
    user_type_name = ((user_data.get("userType") or {}).get("name") or "").lower()

    request.session["user"] = {
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

    request.session["hrms_cookies"] = hrms_cookies

    return {"ok": True, "message": message, "userType": user_type_name}







# ---------------------------------------------------------- LOGOUT ----------------------------------------------------------
@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"ok": True}
