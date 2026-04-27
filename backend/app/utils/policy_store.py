from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

_POLICY_PATH = Path(__file__).with_name("leave_and_attendance_policy.json")

@lru_cache(maxsize=1)
def load_policy_doc() -> Dict[str, Any]:
    with _POLICY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)

def search_policy(
    *,
    query: Optional[str] = None,
    section_title: Optional[str] = None,
    section_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Returns:
      - full doc if no filters
      - matching sections if query/title/id provided
    """
    doc = load_policy_doc()
    sections: List[Dict[str, Any]] = list(doc.get("sections", []))

    if section_id:
        sections = [s for s in sections if str(s.get("id")) == str(section_id)]

    if section_title:
        t = section_title.strip().lower()
        sections = [s for s in sections if t in str(s.get("title", "")).lower()]

    if query:
        q = query.strip().lower()
        def section_text(s: Dict[str, Any]) -> str:
            # search across title + content + table rows
            parts = [str(s.get("title", ""))]
            content = s.get("content")
            if isinstance(content, list):
                parts.extend([str(x) for x in content])
            rows = s.get("rows")
            if isinstance(rows, list):
                parts.append(json.dumps(rows, ensure_ascii=False))
            return " ".join(parts).lower()

        sections = [s for s in sections if q in section_text(s)]

    return {
        "document": doc.get("document", {}),
        "approval": doc.get("approval", {}),
        "sections": sections if (query or section_title or section_id) else doc.get("sections", []),
        "management_rights": next((s for s in doc.get("sections", []) if s.get("id") == "management_rights"), None)
    }