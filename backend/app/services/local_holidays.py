from __future__ import annotations

from typing import Any, Dict, Optional

from app.utils.holiday_store import query_holidays


async def company_holidays(
    *,
    date: Optional[str] = None,   # "YYYY-MM-DD"
    name: Optional[str] = None,   # e.g. "Diwali"
    year: Optional[int] = None,
    **_kw: Any,
) -> Dict[str, Any]:
    data = query_holidays(date=date, name=name, year=year)
    return {"ok": True, **data}