"""
app/core/config.py
──────────────────
FIXED VERSION: Adds .env file existence checking and better validation.

All settings in one place. Reads .env from the project root
using an absolute path so it works regardless of cwd (fixes
the Windows uvicorn --reload subprocess issue).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env sits two levels up from this file:  app/core/config.py  →  project root
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

# FIXED: Check if .env exists before loading
if not _ENV_PATH.exists():
    print(f"⚠️  WARNING: .env file not found at {_ENV_PATH}")
    print("⚠️  Please create a .env file with the following variables:")
    print("    GROQ_API_KEY=your_groq_api_key")
    print("    ELEVENLABS_API_KEY=your_elevenlabs_api_key")
    print("    ELEVENLABS_VOICE_ID=voice_id (optional)")
else:
    load_dotenv(dotenv_path=_ENV_PATH)


class Settings:
    # ── LLM ───────────────────────────────────────────────────
    GROQ_API_KEY: str        = os.getenv("GROQ_API_KEY", "")
    LLM_MODEL: str           = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_TEMPERATURE: float   = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: int      = int(os.getenv("LLM_MAX_TOKENS", "500"))

    # ── ElevenLabs TTS ────────────────────────────────────────
    ELEVENLABS_API_KEY: str  = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tjm4uBm3Mek5FEqMN")
    ELEVENLABS_MODEL: str    = os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")

    # ── Server ────────────────────────────────────────────────
    HOST: str  = os.getenv("HOST", "0.0.0.0")
    PORT: int  = int(os.getenv("PORT", "8000"))

    # ── Paths ─────────────────────────────────────────────────
    BASE_DIR: Path      = Path(__file__).resolve().parents[2]
    DATA_DIR: Path      = BASE_DIR / "app" / "data"
    STATIC_DIR: Path    = BASE_DIR / "app" / "static"
    TEMPLATES_DIR: Path = BASE_DIR / "app" / "templates"

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: list = ["*"]

    @classmethod
    def validate(cls) -> bool:
        """
        FIXED: More comprehensive validation with helpful error messages.
        """
        ok = True
        
        if not cls.GROQ_API_KEY:
            print("⚠️  GROQ_API_KEY is missing!")
            print("    Get your API key from: https://console.groq.com/keys")
            ok = False
            
        if not cls.ELEVENLABS_API_KEY:
            print("⚠️  ELEVENLABS_API_KEY is missing!")
            print("    Get your API key from: https://elevenlabs.io/app/settings/api-keys")
            ok = False
        
        # Check if required directories exist
        if not cls.DATA_DIR.exists():
            print(f"⚠️  Data directory not found: {cls.DATA_DIR}")
            print(f"    Creating directory...")
            cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
            
        if not cls.STATIC_DIR.exists():
            print(f"⚠️  Static directory not found: {cls.STATIC_DIR}")
            ok = False
            
        if not cls.TEMPLATES_DIR.exists():
            print(f"⚠️  Templates directory not found: {cls.TEMPLATES_DIR}")
            ok = False
        
        return ok


settings = Settings()