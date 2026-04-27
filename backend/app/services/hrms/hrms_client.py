from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import httpx

from app.config import settings




class HRMSClient:
    def __init__(self, transport_or_client: httpx.AsyncHTTPTransport | httpx.AsyncClient) -> None:
        if isinstance(transport_or_client, httpx.AsyncClient):
            self.transport = transport_or_client._transport
        else:
            self.transport = transport_or_client
        self.base_url = settings.HRMS_BASE_URL.rstrip("/")

    async def authenticate(
        self,
        *,
        userName: str,
        password: str,
        registrationToken: str,
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, str], int, str, Dict[str, str]]:
        """Never raises on 4xx/5xx. Returns (json_or_none, cookies, status_code, raw_text, headers)."""
        url = f"{self.base_url.rstrip('/')}/{settings.HRMS_AUTH_PATH.lstrip('/')}"
        payload = {"userName": userName, "password": password, "registrationToken": registrationToken}

        # Reuse shared transport for connection pooling + isolated client for cookies
        async with httpx.AsyncClient(transport=self.transport, timeout=30, follow_redirects=True) as client:
            resp = await client.post(
                url,
                data=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "PostmanRuntime/7.0.0",
                },
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
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        # Reuse shared transport for connection pooling + isolated client for cookies
        async with httpx.AsyncClient(transport=self.transport, timeout=30, follow_redirects=True) as client:
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

    async def post(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        cookies: Optional[Dict[str, str]] = None,
    ) -> tuple[int, Dict[str, str], str, Optional[dict]]:
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"
        # Reuse shared transport for connection pooling + isolated client for cookies
        async with httpx.AsyncClient(transport=self.transport, timeout=30, follow_redirects=True) as client:
            resp = await client.post(
                url,
                params=params or {},
                json=json_body,
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
