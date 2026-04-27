from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

_HOLIDAYS_PATH = Path(__file__).with_name("holidays.json")

@lru_cache(maxsize=1)
def load_holidays_doc() -> Dict[str, Any]:
    """Loads backend/app/utils/holidays.json once and caches it."""
    with _HOLIDAYS_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def query_holidays(
    *,
    date: Optional[str] = None,   # "YYYY-MM-DD"
    name: Optional[str] = None,   # partial match
    year: Optional[int] = None,
) -> Dict[str, Any]:
    doc = load_holidays_doc()
    holidays: List[Dict[str, Any]] = list(doc.get("holidays", []))

    if year is not None:
        y = str(year)
        holidays = [h for h in holidays if str(h.get("date", "")).startswith(y)]
    
    if date:
        holidays = [h for h in holidays if h.get("date") == date]

    if name:
        n = name.strip().lower()
        holidays = [h for h in holidays if n in str(h.get("name", "")).lower()]

    return {
        "meta": {
            "company": doc.get("company"),
            "document_title": doc.get("document_title"),
            "year": doc.get("year"),
        },
        "holidays": holidays,
        "policy": doc.get("policy"),
        "notes": doc.get("notes"),
        "approval": doc.get("approval"),
    }