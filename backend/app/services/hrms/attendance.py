from __future__ import annotations

from typing import Any, Dict, Optional

from app.config import settings
from app.services.hrms.hrms_client import HRMSClient



async def _get_with_fallback(
    hrms: HRMSClient,
    primary_path: str,
    fallback_path: str,
    *,
    params: Dict[str, Any],
    hrms_cookies: Dict[str, str],
) -> tuple[int, Optional[dict], str]:
    if not hrms_cookies:
        return 401, None, "No session"
    status, headers, raw, js = await hrms.get(primary_path, params=params, cookies=hrms_cookies)
    if js is not None:
        return status, js, raw

    status2, headers2, raw2, js2 = await hrms.get(fallback_path, params=params, cookies=hrms_cookies)
    return status2, js2, raw2


async def get_attendance_daywise(
    *,
    hrms: HRMSClient,
    month: int,
    year: int,
    hrms_cookies: Dict[str, str],
) -> Dict[str, Any]:
    params = {"month": month, "year": year}
    status, js, raw = await _get_with_fallback(hrms, settings.HRMS_DAYWISE_PATH_PRIMARY, settings.HRMS_DAYWISE_PATH_FALLBACK, params=params, hrms_cookies=hrms_cookies)

    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}
    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    return {"ok": True, "month": month, "year": year, "rows": js.get("DATA") or []}


async def get_attendance_monthsummary(
    *,
    hrms: HRMSClient,
    month: int,
    year: int,
    hrms_cookies: Dict[str, str],
) -> Dict[str, Any]:
    params = {"month": month, "year": year}
    status, js, raw = await _get_with_fallback(hrms, settings.HRMS_MONTHSUMMARY_PATH_PRIMARY, settings.HRMS_MONTHSUMMARY_PATH_FALLBACK, params=params, hrms_cookies=hrms_cookies)

    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}
    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    return {"ok": True, "month": month, "year": year, "data": js.get("DATA") or {}}
