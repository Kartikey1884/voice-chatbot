# app/services/tool_router.py

from datetime import date
from app.services.tools import TOOLS
from app.services.http_client import call_api


def route_tool(tool_name: str, args: dict, cookies: dict):
    if tool_name not in TOOLS:
        return None

    if tool_name == "leave_summary":
        user_id = args["employee_id"]

        today = date.today()
        from_date = today.replace(day=1).strftime("%d-%m-%Y")
        to_date = today.replace(day=28).strftime("%d-%m-%Y")

        endpoint = (
            f"/Hrms/mobile/leave/get/leavesummary"
            f"?fromDate={from_date}"
            f"&toDate={to_date}"
            f"&userId={user_id}"
        )

        return call_api(endpoint, cookies)