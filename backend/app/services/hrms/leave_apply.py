from __future__ import annotations

from typing import Any, Dict
import json

from app.config import settings
from app.services.hrms.hrms_client import HRMSClient



async def get_leave_types(*, hrms: HRMSClient, hrms_cookies: Dict[str, str]) -> Dict[str, Any]:
    if not hrms_cookies:
        return {"ok": False, "message": "No HRMS session found. Please log in again."}
    status, headers, raw, js = await hrms.get(settings.HRMS_LEAVETYPE_PRIMARY, params={}, cookies=hrms_cookies)
    if js is None:
        status, headers, raw, js = await hrms.get(settings.HRMS_LEAVETYPE_FALLBACK, params={}, cookies=hrms_cookies)

    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}
    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    return {"ok": True, "types": js.get("DATA") or []}


async def save_leave_request(*, hrms: HRMSClient, payload: Dict[str, Any], hrms_cookies: Dict[str, str]) -> Dict[str, Any]:
    if not hrms_cookies:
        return {"ok": False, "message": "No HRMS session found. Please log in again."}
    # HRMS expects GET with query params; leaveRequestDates must be JSON string
    params = dict(payload)

    if isinstance(params.get("leaveRequestDates"), list):
        params["leaveRequestDates"] = json.dumps(params["leaveRequestDates"])

    status, headers, raw, js = await hrms.get(settings.HRMS_SAVE_PRIMARY, params=params, cookies=hrms_cookies)
    if js is None:
        status, headers, raw, js = await hrms.get(settings.HRMS_SAVE_FALLBACK, params=params, cookies=hrms_cookies)

    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}

    return {"ok": True, "http": status, "json": js}
