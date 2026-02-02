"""
app/services/text_to_speech.py
──────────────────────────────
Converts text → base64 MP3 audio using ElevenLabs.

FIXED: Works with ElevenLabs API v1.0+
Supports English + All Indian languages
"""

import base64
import asyncio
from elevenlabs.client import ElevenLabs

from app.core.config import settings
from app.core.logging import logger

# Singleton client
_client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)

# ── Voice map: language code → ElevenLabs voice ID ───────────
_DEFAULT_VOICE = settings.ELEVENLABS_VOICE_ID

# English + All Major Indian Languages
VOICE_MAP: dict[str, str] = {
    "en": _DEFAULT_VOICE,   # English
    "hi": _DEFAULT_VOICE,   # Hindi
    "bn": _DEFAULT_VOICE,   # Bengali
    "te": _DEFAULT_VOICE,   # Telugu
    "mr": _DEFAULT_VOICE,   # Marathi
    "ta": _DEFAULT_VOICE,   # Tamil
    "gu": _DEFAULT_VOICE,   # Gujarati
    "kn": _DEFAULT_VOICE,   # Kannada
    "ml": _DEFAULT_VOICE,   # Malayalam
    "or": _DEFAULT_VOICE,   # Odia
    "pa": _DEFAULT_VOICE,   # Punjabi
    "as": _DEFAULT_VOICE,   # Assamese
    "ur": _DEFAULT_VOICE,   # Urdu
}


async def generate_speech(text: str, language: str = "en") -> str:
    """
    Synthesise text into audio and return it as a base64 string.

    Args:
        text: The words to speak.
        language: Two-letter ISO code; falls back to English if unknown.

    Returns:
        Base64-encoded MP3 audio ready for the frontend.
    """
    if not text or not text.strip():
        logger.warning("⚠️  generate_speech called with empty text")
        return ""

    lang_code = (language or "en")[:2].lower()
    voice_id = VOICE_MAP.get(lang_code, _DEFAULT_VOICE)

    logger.info("🔊 TTS → voice=%s lang=%s chars=%d", voice_id[:12], lang_code, len(text))

    def _blocking():
        """ElevenLabs SDK is synchronous — run in a thread."""
        try:
            # Method 1: Try the newer convert method
            audio_bytes = _client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id=settings.ELEVENLABS_MODEL,
            )
            return b"".join(audio_bytes)
            
        except AttributeError:
            # Method 2: Try direct API call (most reliable)
            logger.info("Trying direct API method...")
            import requests
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": settings.ELEVENLABS_API_KEY
            }
            
            data = {
                "text": text,
                "model_id": settings.ELEVENLABS_MODEL,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code != 200:
                error_detail = response.json() if response.content else "Unknown error"
                raise Exception(f"ElevenLabs API error: {error_detail}")
            
            return response.content

    loop = asyncio.get_event_loop()
    audio = await loop.run_in_executor(None, _blocking)

    logger.info("✅ TTS complete — %d bytes", len(audio))
    return base64.b64encode(audio).decode("utf-8")


def get_supported_languages() -> list[str]:
    """Return the language codes we have voices for."""
    return list(VOICE_MAP.keys())