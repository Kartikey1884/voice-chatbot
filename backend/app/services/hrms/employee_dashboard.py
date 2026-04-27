from __future__ import annotations

from typing import Any, Dict

from app.config import settings
from app.services.hrms.hrms_client import HRMSClient



async def get_employee_dashboard_summary(*, hrms: HRMSClient, hrms_cookies: Dict[str, str]) -> Dict[str, Any]:
    if not hrms_cookies:
        return {"ok": False, "message": "No HRMS session found. Please log in again."}
    status, headers, raw, js = await hrms.get(settings.HRMS_DASHBOARD_SUMMARY_PATH, params={}, cookies=hrms_cookies)

    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}
    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    data = js.get("DATA") or {}
    return {
        "ok": True,
        "attendanceSummary": data.get("attendanceSummary") or {},
        "irregularAttendances": data.get("irregularAttendances") or [],
        "leaveSummary": data.get("leaveSummary") or [],
        "notificationCount": data.get("notificationCount"),
        "upcomingBirthDayAndAnniversary": data.get("upcomingBirthDayAndAnniversary") or [],
        "imageBaseUrl": js.get("imageBaseUrl"),
    }
