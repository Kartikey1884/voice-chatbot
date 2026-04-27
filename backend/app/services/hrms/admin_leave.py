from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.hrms.hrms_client import HRMSClient



def _extract_balances(leave_obj: Dict[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for leave_type, info in (leave_obj or {}).items():
        try:
            out[leave_type] = float((info or {}).get("balance", 0.0))
        except Exception:
            continue
    return out


async def get_leave_summary_admin(
    *,
    hrms: HRMSClient,
    fromDate: str,
    toDate: str,
    hrms_cookies: Dict[str, str],
    userId: Optional[int] = None,
) -> Dict[str, Any]:
    if not hrms_cookies:
        return {"ok": False, "message": "No HRMS session found. Please log in again."}
    params: Dict[str, Any] = {"fromDate": fromDate, "toDate": toDate}
    if userId is not None:
        params["userId"] = userId

    status, headers, raw, js = await hrms.get(settings.HRMS_LEAVE_SUMMARY_PATH, params=params, cookies=hrms_cookies)
    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}
    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    data = js.get("DATA") or []
    simplified = []
    for row in data:
        user = (row or {}).get("user") or {}
        leave = (row or {}).get("leave") or {}
        simplified.append({"userId": user.get("id"), "name": user.get("name"), "balances": _extract_balances(leave)})

    return {"ok": True, "fromDate": fromDate, "toDate": toDate, "rows": simplified}


async def get_user_details_admin(
    *,
    hrms: HRMSClient,
    fromDate: str,
    toDate: str,
    userId: int,
    hrms_cookies: Dict[str, str],
) -> Dict[str, Any]:
    if not hrms_cookies:
        return {"ok": False, "message": "No HRMS session found. Please log in again."}
    params: Dict[str, Any] = {"fromDate": fromDate, "toDate": toDate, "userId": userId}

    status, headers, raw, js = await hrms.get(settings.HRMS_LEAVE_SUMMARY_PATH, params=params, cookies=hrms_cookies)
    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}
    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    data: List[Dict[str, Any]] = js.get("DATA") or []
    if not data:
        return {"ok": False, "http": status, "message": f"No user found for userId={userId}."}

    row = data[0] or {}
    user = row.get("user") or {}
    user_details = row.get("user_Details") or {}
    leave = row.get("leave") or {}

    return {
        "ok": True,
        "fromDate": fromDate,
        "toDate": toDate,
        "userId": user.get("id") or userId,
        "name": user.get("name"),
        "email": user.get("email"),
        "mobile": user.get("mobile"),
        "balances": _extract_balances(leave),
        "details": {
            "attendanceCode": user_details.get("attendanceCode"),
            "departmentName": user_details.get("departmentName"),
            "designationName": user_details.get("designationName"),
            "companyName": user_details.get("companyName"),
            "locationName": user_details.get("locationName"),
            "dateOfJoining": user_details.get("dateOfJoining"),
            "dob": user_details.get("dob"),
            "gender": user_details.get("gender"),
            "permanentPin": user_details.get("permanentPin"),
            "permanentAddress": user_details.get("permanentAddress"),
        },
        "raw": {"user": user, "user_Details": user_details},
    }


async def get_on_leave_admin(
    *,
    hrms: HRMSClient,
    fromDate: str,
    toDate: str,
    hrms_cookies: Dict[str, str],
) -> Dict[str, Any]:
    if not hrms_cookies:
        return {"ok": False, "message": "No HRMS session found. Please log in again."}
    status, headers, raw, js = await hrms.get(settings.HRMS_LEAVE_TODAY_PATH, params={"fromDate": fromDate, "toDate": toDate}, cookies=hrms_cookies)
    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}
    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    rows = []
    for x in (js.get("DATA") or []):
        rows.append({"userId": x.get("id"), "name": x.get("name"), "attendanceType": x.get("attendance_type")})

    return {"ok": True, "fromDate": fromDate, "toDate": toDate, "rows": rows}
