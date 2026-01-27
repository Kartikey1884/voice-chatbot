"""
Logging configuration with Windows multiprocessing support
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = Path(__file__).resolve().parents[2] / "logs"
logs_dir.mkdir(exist_ok=True)

# Configure logging
log_file = logs_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"

# Fix Windows encoding for both main and subprocess
if sys.platform == "win32":
    # Force UTF-8 encoding for stdout/stderr
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

# Create handlers with explicit UTF-8 encoding and error handling
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Console handler with error='replace' to handle encoding issues gracefully
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        file_handler,
        console_handler
    ]
)

logger = logging.getLogger(__name__)