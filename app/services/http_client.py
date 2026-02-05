# app/services/http_client.py

import requests
from app.core.config import settings


def call_api(path: str, cookies: dict):
    """
    Calls HRMS APIs using session cookies.
    """
    url = f"{settings.HRMS_BASE_URL}{path}"

    r = requests.get(
        url,
        cookies=cookies,
        timeout=10
    )
    r.raise_for_status()
    return r.json()