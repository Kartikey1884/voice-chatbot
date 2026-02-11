from __future__ import annotations
from typing import Any, Dict, List, Optional
import json
from app.services.groq import GroqLLM
from app.services.prompt_builder import build_system_prompt
from app.services.hrms.admin_leave import get_leave_summary_admin, get_on_leave_admin
from app.core.time_utils import today_ist, month_start_end, fmt_ddmmyyyy_dash

ADMIN_ACTION_KEYWORDS = (
    "leave",
    "leaves",
    "leave balance",
    "leave summary",
    "who is on leave",
    "on leave",
    "absent",
    "paid leave",
)

def is_admin_action(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ADMIN_ACTION_KEYWORDS)


llm = GroqLLM()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "admin_get_leave_summary",
            "description": "Get leave balances summary for all employees or a specific employee (admin only).",
            "parameters": {
                "type": "object",
                "properties": {
                    "fromDate": {"type": "string", "description": "dd-mm-yyyy"},
                    "toDate": {"type": "string", "description": "dd-mm-yyyy"},
                    "userId": {"type": "integer", "description": "optional employee userId"}
                },
                "required": ["fromDate", "toDate"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "admin_get_people_on_leave",
            "description": "Get list of employees on leave/absent for a date or range (admin only).",
            "parameters": {
                "type": "object",
                "properties": {
                    "fromDate": {"type": "string", "description": "dd-mm-yyyy"},
                    "toDate": {"type": "string", "description": "dd-mm-yyyy"}
                },
                "required": ["fromDate", "toDate"]
            }
        }
    }
]

def _default_month_range() -> tuple[str, str]:
    d = today_ist()
    s, e = month_start_end(d)
    return fmt_ddmmyyyy_dash(s), fmt_ddmmyyyy_dash(e)

def _format_leave_summary(result: Dict[str, Any]) -> str:
    if not result.get("ok"):
        return f"Could not fetch leave summary. {result.get('message','')}"

    rows = result.get("rows", [])
    if not rows:
        return f"No leave balance data found for {result['fromDate']} to {result['toDate']}."

    lines = [f"Leave balances ({result['fromDate']} → {result['toDate']}):"]
    for r in rows:
        name = r.get("name") or "Unknown"
        uid = r.get("userId")
        balances = r.get("balances") or {}
        if not balances:
            bal_str = "No leave types returned"
        else:
            bal_str = ", ".join([f"{k}: {v}" for k, v in balances.items()])
        lines.append(f"- {name} (ID: {uid}) → {bal_str}")
    return "\n".join(lines)

def _format_on_leave(result: Dict[str, Any]) -> str:
    if not result.get("ok"):
        return f"Could not fetch on-leave list. {result.get('message','')}"
    rows = result.get("rows", [])
    if not rows:
        return f"No entries for {result['fromDate']} to {result['toDate']}."
    lines = [f"People on leave/absent ({result['fromDate']} → {result['toDate']}):"]
    for r in rows:
        lines.append(f"- {r.get('name')} (ID: {r.get('userId')}) → {r.get('attendanceType')}")
    return "\n".join(lines)

async def admin_chat_once(*, user: Dict, hrms_cookies: Dict[str, str], user_text: str) -> str:
    t = user_text.lower()

    # 1️⃣ Hard rule: admin self-leave not allowed
    if any(x in t for x in ["my leave", "apply leave", "leave for me"]):
        return "Admin does not have leave functionality. Leave management is only for employees."

    # 2️⃣ If NOT an admin action → normal chat, NO TOOLS
    if not is_admin_action(user_text):
        messages = [
            {"role": "system", "content": build_system_prompt(user)},
            {"role": "user", "content": user_text},
        ]
        res = llm.chat(messages)  # ❌ no tools here
        return res.choices[0].message.content or "Okay."

    fromDate, toDate = _default_month_range()

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": build_system_prompt(user)},
        {"role": "user", "content": f"""
User message: {user_text}

If user did not specify dates, use default range:
fromDate={fromDate}, toDate={toDate}.
Date format must be dd-mm-yyyy.
"""}
    ]

    first = llm.chat(messages, tools=TOOLS, tool_choice="auto")
    choice = first.choices[0].message

    # If no tool call, just return model text
    if not getattr(choice, "tool_calls", None):
        return choice.content or "Okay."

    tool_call = choice.tool_calls[0]
    fn = tool_call.function.name
    args = json.loads(tool_call.function.arguments or "{}")

    # Fill defaults if missing
    args.setdefault("fromDate", fromDate)
    args.setdefault("toDate", toDate)

    if fn == "admin_get_leave_summary":
        result = await get_leave_summary_admin(
            fromDate=args["fromDate"],
            toDate=args["toDate"],
            userId=args.get("userId"),
            hrms_cookies=hrms_cookies,
        )
        return _format_leave_summary(result)

    if fn == "admin_get_people_on_leave":
        result = await get_on_leave_admin(
            fromDate=args["fromDate"],
            toDate=args["toDate"],
            hrms_cookies=hrms_cookies,
        )
        return _format_on_leave(result)

    return "Unsupported request."
