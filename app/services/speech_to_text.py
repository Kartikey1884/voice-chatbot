"""
app/services/speech_to_text.py
──────────────────────────────
FIXED VERSION: Uses Groq Whisper API for server-side speech-to-text.

The browser records audio, converts it to WAV, and sends the base64-encoded
WAV data to the server. This service decodes the audio and uses Groq's
Whisper model to transcribe it.

This fixes the mismatch where the code was expecting text but receiving audio.
"""

import base64
import io
from groq import Groq
from app.core.config import settings
from app.core.logging import logger

# Initialize Groq client for Whisper
_whisper_client = Groq(api_key=settings.GROQ_API_KEY)


async def transcribe_from_payload(payload_b64: str) -> tuple[str, str]:
    """
    Transcribe audio using Groq Whisper API.

    The frontend sends base64-encoded WAV audio. This function:
    1. Decodes the base64 audio data
    2. Sends it to Groq Whisper for transcription
    3. Returns the transcript and detected language

    Args:
        payload_b64: base64-encoded WAV audio data.

    Returns:
        (transcript, language_code)
    """
    try:
        # Decode base64 audio
        audio_data = base64.b64decode(payload_b64)
        
        # Create file-like object for Groq API
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "audio.wav"
        
        logger.info("🎤 Sending audio to Whisper (%d bytes)", len(audio_data))
        
        # Call Groq Whisper API
        transcription = _whisper_client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3",
            response_format="verbose_json",
            language=None,  # Auto-detect language
        )
        
        text = transcription.text.strip()
        language = transcription.language or "en"
        
    except Exception as exc:
        logger.error("❌ Failed to transcribe audio: %s", exc)
        raise ValueError("Could not transcribe the audio") from exc

    # ── validation ────────────────────────────────────────────
    if not text or len(text) < 1:
        logger.warning("⚠️  Whisper: transcript too short or empty")
        raise ValueError("Transcript is empty or too short")

    # Simple gibberish filter: if the unique characters (ignoring spaces)
    # are ≤ 2 it's probably noise, not real speech.
    unique_chars = len(set(text.lower().replace(" ", "")))
    if unique_chars <= 2:
        logger.warning("⚠️  Whisper: possible gibberish detected — '%s'", text)
        raise ValueError("Transcript doesn't look like real speech")

    logger.info("✅ Whisper transcript: '%s' (lang=%s)", text, language)
    return text, language


def get_supported_languages() -> list[str]:
    """Languages that Whisper supports (non-exhaustive list)."""
    return [
        "en", "es", "fr", "de", "it", "pt", "ru",
        "ja", "ko", "zh", "hi", "ar", "tr", "pl",
        "nl", "sv", "da", "no", "fi", "cs", "el",
        "he", "id", "th", "uk", "vi", "ro", "ca",
    ]
