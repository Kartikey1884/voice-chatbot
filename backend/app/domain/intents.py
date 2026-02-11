LEAVE_KEYWORDS = (
    "leave", "leaves", "leave balance", "remaining", "pl", "so", "sick",
    "holiday", "vacation", "time off", "apply leave", "take leave", "off"
)

def is_leave_topic(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in LEAVE_KEYWORDS)
