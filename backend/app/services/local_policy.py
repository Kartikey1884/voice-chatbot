from __future__ import annotations

from typing import Any, Dict, Optional
from app.utils.policy_store import search_policy

async def leave_attendance_policy(
    *,
    query: Optional[str] = None,
    section_title: Optional[str] = None,
    section_id: Optional[str] = None,
    **_kw: Any
) -> Dict[str, Any]:
    data = search_policy(query=query, section_title=section_title, section_id=section_id)
    return {"ok": True, **data}