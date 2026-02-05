import requests
from fastapi import HTTPException
from app.core.config import settings

class HRMSClient:
    def __init__(self):
        self.base_url = settings.HRMS_BASE_URL

    def login(self, username: str, password: str, registration_token: str):
        url = f"{self.base_url}/Hrms/mobile/user/authenticate"

        response = requests.post(
            url,
            files={
                "userName": (None, username),
                "password": (None, password),
                "registrationToken": (None, registration_token),
            }
        )

        # Parse JSON first
        data = response.json()

        # 🔴 BUSINESS VALIDATION (THIS WAS MISSING)
        if data.get("STATUS") != 1:
            raise HTTPException(
                status_code=401,
                detail=data.get("MESSAGE", "Invalid username or password")
            )

        return {
            "json": data,
            "cookies": response.cookies.get_dict()
        }
