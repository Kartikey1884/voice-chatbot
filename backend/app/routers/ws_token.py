import uuid
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api", tags=["ws"])

@router.get("/ws-token")
async def ws_token(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = str(uuid.uuid4())
    request.session["ws_token"] = token
    return {"token": token, "user": user}
