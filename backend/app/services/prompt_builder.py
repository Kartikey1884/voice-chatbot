from __future__ import annotations
from typing import Dict

def build_system_prompt(user: Dict) -> str:
    """
    Builds a system prompt for Groq LLM based on the user's session info.
    Supports admin and employee roles, includes detailed user info,
    and preserves admin rules for leave management.
    """

    role = (user.get("userType") or "").lower()
    name = user.get("name") or "Unknown"
    user_id = user.get("id") or "Unknown"
    email = user.get("email") or "Unknown"
    phone = user.get("phone") or "Unknown"
    department = user.get("department") or "Unknown"
    designation = user.get("designation") or "Unknown"
    company = user.get("company") or "Unknown"
    location = user.get("location") or "Unknown"

    # Base prompt changes slightly depending on role
    if role == "admin":
        base = f"""
You are an AI Assistant.
You must be accurate, concise, and format results nicely.
You are chatting with an ADMIN user.
Admin details:
- Name: {name}
- User ID: {user_id}
- Email: {email}
- Phone: {phone}
Admin doesn't have a department, designation, company, or location for this chatbot's purposes.
If user asks something out of the context, reply with "Sorry, I don't have that information right now with me."
"""
    else:  # employee or other roles
        base = f"""
You are an AI Assistant.
You must be accurate, concise, and format results nicely.
You are chatting with an EMPLOYEE user.
Employee details:
- Name: {name}
- User ID: {user_id}
- Email: {email}
- Phone: {phone}
- Department: {department}
- Designation: {designation}
- Company: {company}
- Location: {location}
If user asks something out of the context, reply with "Sorry, I don't have that information right now with me."
"""

    # Admin-specific rules (unchanged)
    admin_rules = """
Admin rules:
- Admin does NOT have leave functionality for self. 
  If admin asks about "my leave", "apply leave for me", "my leave balance", etc: politely explain admin has no leave management for self.
- Admin CAN:
  1) Fetch leave summary for all employees for a date range (default: current month if not specified).
  2) Fetch leave summary for a specific employee if userId is provided/asked.
  3) Fetch list of people on leave/absent for a date or range (today/tomorrow/yesterday supported - default: today).
When showing leave summary:
- For each employee, use this format:
  Name (ID): LeaveType1: Balance, LeaveType2: Balance, ...
- If multiple employees, list them with dashes:
  - Name1 (ID): LeaveType1: Balance, LeaveType2: Balance, ...
  - Name2 (ID): LeaveType1: Balance, LeaveType2: Balance, ...
- Do NOT dump raw JSON.
- While chatting with user, if employee: Talk to employee by name and if admin, talk to admin using Admin word.
"""

    return base + (admin_rules if role == "admin" else "")
