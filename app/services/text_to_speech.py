"""
Text-to-Speech module using Edge TTS (Free Microsoft voices)
"""

import base64
import edge_tts


# Voice mapping for different languages
VOICE_MAP = {
    "en": "en-US-AriaNeural",      # English - Female, natural
    "hi": "hi-IN-SwaraNeural",      # Hindi - Female
    "es": "es-ES-ElviraNeural",     # Spanish - Female
    "fr": "fr-FR-DeniseNeural",     # French - Female
    "de": "de-DE-KatjaNeural",      # German - Female
    "pt": "pt-BR-FranciscaNeural",  # Portuguese - Female
    "it": "it-IT-ElsaNeural",       # Italian - Female
    "ja": "ja-JP-NanamiNeural",     # Japanese - Female
    "ko": "ko-KR-SunHiNeural",      # Korean - Female
    "zh": "zh-CN-XiaoxiaoNeural",   # Chinese - Female
    "ru": "ru-RU-SvetlanaNeural",   # Russian - Female
    "ar": "ar-SA-ZariyahNeural",    # Arabic - Female
}


async def generate_speech(text: str, language: str = "en") -> str:
    """
    Convert text to speech using Edge TTS
    
    Args:
        text: Text to convert to speech
        language: Language code (e.g., 'en', 'hi', 'es')
    
    Returns:
        str: Base64 encoded audio data (MP3 format)
    
    Example:
        audio_base64 = await generate_speech("Hello world", "en")
    """
    # Select appropriate voice based on language
    language_code = language[:2].lower()
    voice = VOICE_MAP.get(language_code, "en-US-AriaNeural")
    
    # Create TTS communication
    communicate = edge_tts.Communicate(text, voice)
    
    # Collect audio chunks
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    
    # Convert to base64 for transmission
    audio_base64 = base64.b64encode(audio_data).decode("utf-8")
    
    return audio_base64


async def get_available_voices():
    """
    Get list of all available Edge TTS voices
    
    Returns:
        list: List of voice dictionaries with details
    """
    voices = await edge_tts.list_voices()
    return [
        {
            "name": v["Name"],
            "language": v["Locale"],
            "gender": v["Gender"],
            "short_name": v["ShortName"]
        }
        for v in voices
    ]


def get_supported_languages():
    """Return list of supported language codes"""
    return list(VOICE_MAP.keys())
