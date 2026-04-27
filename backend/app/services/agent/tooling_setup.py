from __future__ import annotations

from typing import Any, Dict

from app.services.agent.tools import ToolRegistry, ToolSpec
from app.services.hrms.admin_leave import get_leave_summary_admin, get_on_leave_admin, get_user_details_admin
from app.services.hrms.attendance import get_attendance_daywise, get_attendance_monthsummary
from app.services.hrms.employee_dashboard import get_employee_dashboard_summary
from app.services.hrms.leave_apply import get_leave_types, save_leave_request
from app.services.hrms.profile import get_user_profile
from app.services.local_holidays import company_holidays
from app.services.local_policy import leave_attendance_policy


def build_registry() -> ToolRegistry:
    reg = ToolRegistry()
    
    # Holiday List Tool
    reg.register(
        ToolSpec(
            name="company_holidays",
            description=(
                "Get the official company holiday calendar from holidays.json. "
                "Use this when the user asks about holidays, festival holidays, national holidays, upcoming holidays, or official holiday provided by the company, "
                "whether a date is a holiday, or to list holidays."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Filter by exact date in YYYY-MM-DD"},
                    "name": {"type": "string", "description": "Filter by holiday name (partial match allowed)"},
                    "year": {"type": "integer", "description": "Filter by year, e.g. 2026"},
                },
                "required": [],
            },
            handler=lambda **kw: company_holidays(**kw),
        )
    )

    reg.register(
        ToolSpec(
            name="user_profile",
            description="Fetch the logged-in employee's comprehensive profile, including: Bank Details (Acc No, IFSC, Bank Name), KYC (PAN, Adhaar), Personal Details (Gender, DOB, Marital Status, Emergency Contact), and Contact Info (Addresses, Personal Email).",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda **kw: get_user_profile(**kw),
        )
    )

    reg.register(
        ToolSpec(
            name="employee_dashboard_summary",
            description="Fetch a comprehensive overview of the logged-in employee's status, including leave balances (privilege leaves, etc.), today's attendance, and pending notifications. Use this when the user asks for their 'leave balance', 'total leaves', 'attendance status', or a general summary.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda **kw: get_employee_dashboard_summary(**kw),
        )
    )

    reg.register(
        ToolSpec(
            name="attendance_daywise",
            description="Get day-wise attendance for the logged-in employee for a given month and year.",
            parameters={
                "type": "object",
                "properties": {"month": {"type": "integer", "minimum": 1, "maximum": 12}, "year": {"type": "integer", "minimum": 2000, "maximum": 2100}},
                "required": ["month", "year"],
            },
            handler=lambda month, year, **kw: get_attendance_daywise(month=month, year=year, **kw),
        )
    )

    reg.register(
        ToolSpec(
            name="attendance_monthsummary",
            description="Get monthly attendance summary for the logged-in employee for a given month and year.",
            parameters={
                "type": "object",
                "properties": {"month": {"type": "integer", "minimum": 1, "maximum": 12}, "year": {"type": "integer", "minimum": 2000, "maximum": 2100}},
                "required": ["month", "year"],
            },
            handler=lambda month, year, **kw: get_attendance_monthsummary(month=month, year=year, **kw),
        )
    )

    reg.register(
        ToolSpec(
            name="leave_types",
            description="Get available leave types for the logged-in employee.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=lambda **kw: get_leave_types(**kw),
        )
    )

    reg.register(
        ToolSpec(
            name="apply_leave",
            description=(
                "Apply leave for the logged-in employee. "
                "Uses HRMS GET /mobile/leave/save/leaverequest with query params. "
                "Dates: fromDate/toDate in DD-MM-YYYY; leaveRequestDates items use YYYY-MM-DD."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "leaveTypeId": {"type": "integer"},
                    "fromDate": {"type": "string", "description": "DD-MM-YYYY"},
                    "toDate": {"type": "string", "description": "DD-MM-YYYY"},
                    "leaveReason": {"type": "string"},
                    "leaveRequestDates": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {"type": "string", "description": "YYYY-MM-DD"},
                                "halfDay": {"type": "boolean"},
                            },
                            "required": ["date", "halfDay"],
                        },
                    },
                    "leaveRequestId": {"type": "integer"},
                },
                "required": ["leaveTypeId", "fromDate", "toDate", "leaveReason", "leaveRequestDates"],
            },
            handler=lambda leaveTypeId, fromDate, toDate, leaveReason, leaveRequestDates, leaveRequestId=None, **kw: (
                save_leave_request(
                    payload={
                        "leaveTypeId": leaveTypeId,
                        "fromDate": fromDate,
                        "toDate": toDate,
                        "leaveReason": leaveReason,
                        "leaveRequestDates": leaveRequestDates,
                        **({} if leaveRequestId is None else {"leaveRequestId": leaveRequestId}),
                    },
                    **kw,
                )
            ),
        )
    )


    # Admin tools
    reg.register(
        ToolSpec(
            name="admin_leave_summary",
            description="Admin: Get leave summary balances for all employees within a date range (fromDate/toDate in DD-MM-YYYY).",
            parameters={
                "type": "object",
                "properties": {
                    "fromDate": {"type": "string", "description": "DD-MM-YYYY"},
                    "toDate": {"type": "string", "description": "DD-MM-YYYY"},
                },
                "required": ["fromDate", "toDate"],
            },
            handler=lambda fromDate, toDate, **kw: get_leave_summary_admin(fromDate=fromDate, toDate=toDate, **kw),
        )
    )

    reg.register(
        ToolSpec(
            name="admin_user_details",
            description="Admin ONLY: Get detailed employee profile + leave balances for a SPECIFIC userId. Requires you to have the exact integer userId.",
            parameters={
                "type": "object",
                "properties": {
                    "fromDate": {"type": "string", "description": "DD-MM-YYYY"},
                    "toDate": {"type": "string", "description": "DD-MM-YYYY"},
                    "userId": {"type": "integer"},
                },
                "required": ["fromDate", "toDate", "userId"],
            },
            handler=lambda fromDate, toDate, userId, **kw: get_user_details_admin(fromDate=fromDate, toDate=toDate, userId=userId, **kw),
        )
    )

    reg.register(
        ToolSpec(
            name="admin_on_leave",
            description="Admin: List employees on leave within a date range.",
            parameters={
                "type": "object",
                "properties": {"fromDate": {"type": "string"}, "toDate": {"type": "string"}},
                "required": ["fromDate", "toDate"],
            },
            handler=lambda fromDate, toDate, **kw: get_on_leave_admin(fromDate=fromDate, toDate=toDate, **kw),
        )
    )

    reg.register(
        ToolSpec(
            name="leave_attendance_policy",
            description=(
                "Search the company's Leave & Attendance Policy (from leave_and_attendance_policy.json). "
                "Use when user asks about leave rules, attendance rules, late marks, half-day, comp-off, "
                "sandwich policy, unauthorized leave, notice period leave, flexi/short leave, punching rules, encashment."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search text, e.g. 'late mark', 'comp off', 'sandwich'"},
                    "section_title": {"type": "string", "description": "Match by section title, partial allowed"},
                    "section_id": {"type": "string", "description": "Exact section id if known"},
                },
                "required": []
            },
            handler=lambda **kw: leave_attendance_policy(**kw),
        )
    )
        
    return reg
