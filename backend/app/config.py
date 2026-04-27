from __future__ import annotations
import os
from dotenv import load_dotenv

# Load .env file (adjust path as needed)
load_dotenv("../.env")


class Settings:
    """Application settings loaded from environment variables (.env or system env)"""
    
    # App
    APP_NAME: str = os.getenv("APP_NAME", "HRMS AI Chatbot")
    ENV: str = os.getenv("ENV", "dev")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))

    # Security / sessions
    SESSION_SECRET: str = os.getenv("SESSION_SECRET", "CHANGE_ME_SESSION_SECRET")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "sid")
    SESSION_TTL_SECONDS: int = int(os.getenv("SESSION_TTL_SECONDS", 60 * 60 * 8))  # 8 hours

    # Storage
    REDIS_URL: str | None = os.getenv("REDIS_URL")

    # HRMS
    HRMS_BASE_URL: str = os.getenv("HRMS_BASE_URL", "")
    HRMS_AUTH_PATH: str = os.getenv("HRMS_AUTH_PATH", "")
    HRMS_LEAVE_SUMMARY_PATH: str = os.getenv("HRMS_LEAVE_SUMMARY_PATH", "")
    HRMS_LEAVE_TODAY_PATH: str = os.getenv("HRMS_LEAVE_TODAY_PATH", "")
    HRMS_DAYWISE_PATH_PRIMARY: str = os.getenv("HRMS_DAYWISE_PATH_PRIMARY", "")
    HRMS_DAYWISE_PATH_FALLBACK: str = os.getenv("HRMS_DAYWISE_PATH_FALLBACK", "")
    HRMS_MONTHSUMMARY_PATH_PRIMARY: str = os.getenv("HRMS_MONTHSUMMARY_PATH_PRIMARY", "")
    HRMS_MONTHSUMMARY_PATH_FALLBACK: str = os.getenv("HRMS_MONTHSUMMARY_PATH_FALLBACK", "")
    HRMS_DASHBOARD_SUMMARY_PATH: str = os.getenv("HRMS_DASHBOARD_SUMMARY_PATH", "")
    HRMS_LEAVETYPE_PRIMARY: str = os.getenv("HRMS_LEAVETYPE_PRIMARY", "")
    HRMS_LEAVETYPE_FALLBACK: str = os.getenv("HRMS_LEAVETYPE_FALLBACK", "")
    HRMS_SAVE_PRIMARY: str = os.getenv("HRMS_SAVE_PRIMARY", "")
    HRMS_SAVE_FALLBACK: str = os.getenv("HRMS_SAVE_FALLBACK", "")
    HRMS_PROFILE_PATH_PRIMARY: str = os.getenv("HRMS_PROFILE_PATH_PRIMARY", "")
    HRMS_PROFILE_PATH_FALLBACK: str = os.getenv("HRMS_PROFILE_PATH_FALLBACK", "")

    # LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")  # "groq" or "openai"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
    LLM_MAX_TOOL_STEPS: int = int(os.getenv("LLM_MAX_TOOL_STEPS", 4))

    @property
    def LLM_API_KEY(self) -> str:
        if self.LLM_PROVIDER == "groq":
            return os.getenv("GROQ_API_KEY", "")
        return os.getenv("OPENAI_API_KEY", "")


    ## TTS
    # TTS_API_KEY: str | None = os.getenv("ELEVENLABS_API_KEY")
    # TTS_VOICE_ID: str | None = os.getenv("ELEVENLABS_VOICE_ID")
    # TTS_VOICE_MODEL_ID: str | None = os.getenv("ELEVENLABS_MODEL_ID")

    TTS_API_KEY: str | None = os.getenv("SARVAM_API_KEY")
    #TTS_VOICE_ID: str | None = os.getenv("SARVAM_VOICE_ID")
    TTS_VOICE_MODEL: str | None = os.getenv("SARVAM_TTS_MODEL")

    # STT 
    STT_URL: str | None = os.getenv("SARVAM_URL")
    STT_API_KEY: str | None = os.getenv("SARVAM_API_KEY")
    # STT_MODEL: str | None = os.getenv("SARVAM_STT_MODEL", "whisper-1")
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
    # OPENAI_STT_MODEL: str | None = os.getenv("OPENAI_STT_MODEL", "whisper-1")


# Create singleton instance to use everywhere
settings = Settings()
