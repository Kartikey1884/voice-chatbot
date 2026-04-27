from __future__ import annotations

from typing import Any, Dict

from app.config import settings
from app.services.hrms.hrms_client import HRMSClient



async def get_user_profile(*, hrms: HRMSClient, hrms_cookies: Dict[str, str]) -> Dict[str, Any]:
    """
    Fetch the logged-in user's detailed profile information.
    """
    if not hrms_cookies:
        return {"ok": False, "message": "No HRMS session found. Please log in again."}

    status, headers, raw, js = await hrms.get(settings.HRMS_PROFILE_PATH_PRIMARY, params={}, cookies=hrms_cookies)
    if js is None:
        status, headers, raw, js = await hrms.get(settings.HRMS_PROFILE_PATH_FALLBACK, params={}, cookies=hrms_cookies)

    if js is None:
        return {"ok": False, "http": status, "message": "HRMS returned non-JSON", "rawPreview": raw[:300]}
    
    if js.get("STATUS") != 1:
        return {"ok": False, "http": status, "message": js.get("MESSAGE", "HRMS error")}

    data = js.get("DATA") or {}
    user = data.get("user") or {}
    details = data.get("userdetails") or {}

    return {
        "ok": True,
        "basicInfo": {
            "name": user.get("name"),
            "email": user.get("email"),
            "phone": user.get("phone"),
            "employeeId": user.get("id"),
            "department": (user.get("department") or {}).get("name"),
            "designation": (user.get("designation") or {}).get("name"),
            "company": (user.get("company") or {}).get("name"),
        },
        "personalDetails": {
            "gender": details.get("gender"),
            "dateOfBirth": details.get("dob"),
            "maritalStatus": details.get("maritalStatus"),
            "bloodGroup": details.get("bloodGroup"),
            "emergencyContact": details.get("emergencyContact"),
            "personalEmail": details.get("emailPersonal"),
        },
        "kycDetails": {
            "pan": details.get("pan"),
            "adhaar": details.get("adhaar"),
            "bankAccountNo": details.get("acNo"),
            "ifsc": details.get("ifsc"),
            "bankName": details.get("bank"),
            "bankBranch": details.get("bankBranch"),
        },
        "employmentDetails": {
            "department": (user.get("department") or {}).get("name"),
            "designation": (user.get("designation") or {}).get("name"),
            "company": (user.get("company") or {}).get("name"),
            "location": (user.get("location") or {}).get("name"),
            "reportingManager": (user.get("reportsTo") or {}).get("name"),
            "joiningDate": user.get("doj"),
            "confirmationDate": details.get("confirmationDate"),
            "grade": details.get("grade"),
            "employmentType": details.get("employmentType"),
        },
        "address": {
            "present": f"{details.get('presentAddress')}, { (details.get('presentCity') or {}).get('name') or '' }, {details.get('presentPin') or ''}",
            "permanent": f"{details.get('permanentAddress')}, { (details.get('permanentCity') or {}).get('name') or '' }, {details.get('permanentPin') or ''}",
        }
    }
