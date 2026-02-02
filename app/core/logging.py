"""
app/core/logging.py
───────────────────
Configures a single logger used everywhere.
• Writes to  logs/app_YYYYMMDD.log
• Also prints to stdout
• Handles Windows encoding quirks in uvicorn subprocesses
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# ── log directory ─────────────────────────────────────────────
logs_dir = Path(__file__).resolve().parents[2] / "logs"
logs_dir.mkdir(exist_ok=True)

log_file = logs_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

# ── Windows encoding fix ──────────────────────────────────────
if sys.platform == "win32":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# ── handlers ──────────────────────────────────────────────────
_FMT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(_FMT))

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(_FMT))

logging.basicConfig(level=logging.INFO, format=_FMT, handlers=[file_handler, console_handler])

logger = logging.getLogger(__name__)
