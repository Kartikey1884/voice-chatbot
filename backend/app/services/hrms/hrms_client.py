from typing import Any, Dict, Tuple, Optional
import httpx
from app.config import HRMS_BASE_URL

AUTH_PATH = "/Hrms/mobile/user/authenticate"

class HRMSClient:
    def __init__(self) -> None:
        self.base_url = HRMS_BASE_URL

    async def authenticate(
        self,
        userName: str,
        password: str,
        registrationToken: str
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, str], int, str, Dict[str, str]]:
        """
        Calls HRMS authenticate endpoint using x-www-form-urlencoded (Postman style).
        Never raises on 4xx/5xx. Returns (json_or_none, cookies, status_code, raw_text, headers).
        """
        url = f"{self.base_url}{AUTH_PATH}"
        payload = {
            "userName": userName,
            "password": password,
            "registrationToken": registrationToken,
        }

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            resp = await client.post(
                url,
                data=payload,  # ✅ IMPORTANT (form/urlencoded), NOT json=
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "PostmanRuntime/7.0.0",  # helps mimic Postman
                }
            )

        raw_text = resp.text
        cookies = dict(resp.cookies)
        headers = dict(resp.headers)

        try:
            data = resp.json()
        except Exception:
            data = None

        return data, cookies, resp.status_code, raw_text, headers


    async def get(
        self,
        path: str,
        *,
        params: Dict[str, Any],
        cookies: Optional[Dict[str, str]] = None,
    ) -> tuple[int, Dict[str, str], str, Optional[dict]]:
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
            resp = await client.get(
                url,
                params=params,
                cookies=cookies or {},
                headers={"Accept": "application/json", "User-Agent": "PostmanRuntime/7.0.0"},
            )

        raw = resp.text
        headers = dict(resp.headers)
        try:
            js = resp.json()
        except Exception:
            js = None
        return resp.status_code, headers, raw, js
