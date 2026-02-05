import uuid
from datetime import datetime

SESSION_STORE = {}

def create_session(auth_response: dict):
    session_id = str(uuid.uuid4())

    SESSION_STORE[session_id] = {
        "created_at": datetime.utcnow(),
        "hrms": {
            "user": auth_response["json"],     # ✅ FULL USER DETAILS
            "cookies": auth_response["cookies"]
        }
    }

    return session_id


def get_session(session_id: str):
    return SESSION_STORE.get(session_id)
