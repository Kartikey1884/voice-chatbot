from fastapi import HTTPException, Request

def get_user_or_401(request: Request) -> dict:
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def is_admin(user: dict) -> bool:
    return (user.get("userType") or "").lower() == "admin"

def is_employee(user: dict) -> bool:
    return (user.get("userType") or "").lower() == "employee"
