from __future__ import annotations
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import calendar
import re

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    # Windows fallback (system local time)
    IST = None

def today_ist() -> date:
    if IST:
        return datetime.now(IST).date()
    return datetime.now().date()


def month_start_end(d: date) -> tuple[date, date]:
    first = d.replace(day=1)
    last_day = calendar.monthrange(d.year, d.month)[1]
    last = d.replace(day=last_day)
    return first, last

def fmt_ddmmyyyy_dash(d: date) -> str:
    return d.strftime("%d-%m-%Y")

def resolve_relative_day(text: str, base: date | None = None) -> date | None:
    base = base or today_ist()
    t = text.lower()
    if "today" in t:
        return base
    if "tomorrow" in t:
        return base + timedelta(days=1)
    if "yesterday" in t:
        return base - timedelta(days=1)
    return None

def try_parse_ddmmyyyy_dash(s: str) -> date | None:
    # expects dd-mm-yyyy
    m = re.fullmatch(r"(\d{2})-(\d{2})-(\d{4})", s.strip())
    if not m:
        return None
    dd, mm, yyyy = map(int, m.groups())
    return date(yyyy, mm, dd)
