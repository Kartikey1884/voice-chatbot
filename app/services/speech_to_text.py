"""
Speech-to-Text module using Faster Whisper
"""

import asyncio
import tempfile
import os
from faster_whisper import WhisperModel

from app.core.config import settings
from app.core.logging import logger

# Load model at startup (singleton pattern)
logger.info("🚀 Loading Faster Whisper model...")
whisper_model = WhisperModel(
    settings.WHISPER_MODEL, 
    device=settings.WHISPER_DEVICE, 
    compute_type=settings.WHISPER_COMPUTE_TYPE
)
logger.info("✅ Whisper model ready!")


async def transcribe_audio(audio_bytes: bytes) -> tuple[str, str]:
    """
    Transcribe audio to text using Faster Whisper
    
    Args:
        audio_bytes: Raw audio data in bytes (WAV format preferred)
    
    Returns:
        tuple: (transcribed_text, detected_language)
    
    Example:
        text, lang = await transcribe_audio(audio_data)
        print(f"Transcribed ({lang}): {text}")
    """
    # Save audio to temporary file
    # Try WAV first, but Whisper can handle various formats
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
                temperature=0.0,
                vad_filter=True,  # Enable voice activity detection
                vad_parameters=dict(min_silence_duration_ms=500)
            )
        )
        
        # Combine all segments into single text
        text = " ".join([seg.text for seg in segments]).strip()
        language = info.language if hasattr(info, 'language') else "en"
        
        # Ensure language code is 2 characters (Whisper returns full codes like "en", "hi", etc.)
        language = language[:2].lower() if language else "en"
        
        logger.info(f"✅ Transcribed: '{text}' (language: {language})")
        
        return text, language
    
    except Exception as e:
        logger.error(f"❌ Transcription error: {e}")
        # Try with different parameters as fallback
        try:
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: whisper_model.transcribe(
                    tmp_path,
                    language=None,
                    beam_size=1,
                    best_of=1,
                    temperature=0.0
                )
            )
            text = " ".join([seg.text for seg in segments]).strip()
            language = info.language[:2].lower() if hasattr(info, 'language') and info.language else "en"
            logger.info(f"✅ Transcribed (fallback): '{text}' (language: {language})")
            return text, language
        except Exception as e2:
            logger.error(f"❌ Fallback transcription also failed: {e2}")
            raise e
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except:
            pass


def get_supported_languages():
    """Return list of languages supported by Whisper"""
    return [
        "en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh",
        "hi", "ar", "tr", "pl", "nl", "sv", "da", "no", "fi"
    ]
