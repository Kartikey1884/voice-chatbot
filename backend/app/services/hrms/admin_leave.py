from __future__ import annotations
from typing import Any, Dict, Optional, List
from app.services.hrms.hrms_client import HRMSClient

client = HRMSClient()

LEAVE_SUMMARY_PATH = "/Hrms/admin/leave/get/leavesummary"
LEAVE_TODAY_PATH   = "/Hrms/admin/leave/get/leavetypetoday"

def _extract_balances(leave_obj: Dict[str, Any]) -> Dict[str, float]:
    # leave_obj looks like {"PL":{"balance":6.5},"SO":{"balance":0.0}, ...}
    out: Dict[str, float] = {}
    for leave_type, info in (leave_obj or {}).items():
        try:
            out[leave_type] = float((info or {}).get("balance", 0.0))
        except Exception:
            continue
    return out

async def get_leave_summary_admin(
    *,
    fromDate: str,
    toDate: str,
    hrms_cookies: Dict[str, str],
    userId: Optional[int] = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {"fromDate": fromDate, "toDate": toDate}
    if userId is not None:
        params["userId"] = userId

    status, headers, raw, js = await client.get(
        LEAVE_SUMMARY_PATH,
        params=params,
        cookies=hrms_cookies,
    )

    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}

    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    data = js.get("DATA") or []
    simplified = []
    for row in data:
        user = (row or {}).get("user") or {}
        leave = (row or {}).get("leave") or {}
        simplified.append({
            "userId": user.get("id"),
            "name": user.get("name"),
            "balances": _extract_balances(leave),
        })

    return {"ok": True, "fromDate": fromDate, "toDate": toDate, "rows": simplified}

async def get_on_leave_admin(
    *,
    fromDate: str,
    toDate: str,
    hrms_cookies: Dict[str, str],
) -> Dict[str, Any]:
    status, headers, raw, js = await client.get(
        LEAVE_TODAY_PATH,
        params={"fromDate": fromDate, "toDate": toDate},
        cookies=hrms_cookies,
    )

    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}

    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    rows = []
    for x in (js.get("DATA") or []):
        rows.append({
            "userId": x.get("id"),
            "name": x.get("name"),
            "attendanceType": x.get("attendance_type"),
        })

    return {"ok": True, "fromDate": fromDate, "toDate": toDate, "rows": rows}
