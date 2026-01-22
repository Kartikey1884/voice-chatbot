"""
Speech-to-Text module using Faster Whisper
"""

import asyncio
import tempfile
import os
from faster_whisper import WhisperModel

# Load model at startup (singleton pattern)
print("🚀 Loading Faster Whisper model...")
whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
print("✅ Whisper model ready!")


async def transcribe_audio(audio_bytes: bytes) -> tuple[str, str]:
    """
    Transcribe audio to text using Faster Whisper
    
    Args:
        audio_bytes: Raw audio data in bytes
    
    Returns:
        tuple: (transcribed_text, detected_language)
    
    Example:
        text, lang = await transcribe_audio(audio_data)
        print(f"Transcribed ({lang}): {text}")
    """
    # Save audio to temporary file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    
    try:
        # Run transcription in thread pool (CPU-bound operation)
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            lambda: whisper_model.transcribe(
                tmp_path,
                language=None,  # Auto-detect language
                beam_size=5,
                best_of=5,
                temperature=0.0
            )
        )
        
        # Combine all segments into single text
        text = " ".join([seg.text for seg in segments]).strip()
        language = info.language
        
        return text, language
    
    finally:
        # Clean up temporary file
        os.unlink(tmp_path)


def get_supported_languages():
    """Return list of languages supported by Whisper"""
    return [
        "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
        "hi", "ar", "tr", "pl", "nl", "sv", "da", "no", "fi"
    ]