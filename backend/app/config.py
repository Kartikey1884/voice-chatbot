# app/config.py

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

HRMS_BASE_URL = os.getenv("HRMS_BASE_URL", "").strip()
SESSION_SECRET = os.getenv("SESSION_SECRET", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
