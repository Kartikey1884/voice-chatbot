# from langdetect import detect

# def detect_user_language(text: str) -> str:
#     try:
#         lang = detect(text)
#         print(f"Detected language: {lang}")
#         return lang
#     except:
#         return "en"  # Default to English if detection fails

# def get_voice_for_language(lang: str) -> str:
#     """
#     Return best voice_id for Indian multilingual users
#     """

#     if lang == "hi":
#         return "21m00Tcm4TlvDq8ikWAM"  # Hindi-friendly neutral voice

#     if lang in ["gu", "ta", "te", "mr", "bn"]:
#         return "21m00Tcm4TlvDq8ikWAM"  # Multilingual voice works best

#     # Default: Indian English users
#     return "pNInz6obpgDQGcFmaJgB"


from langdetect import detect


def detect_user_language(text: str) -> str:
    try:
        lang = detect(text)
        print(f"Detected language: {lang}")
        return lang
    except:
        return "en"


def get_voice_for_language(lang: str) -> str:
    """
    Return Sarvam speaker name based on language
    """

    voice_map = {
        "hi": "shubh",   # Hindi
        "en": "maya",    # English
        "gu": "shubh",   # Gujarati
        "mr": "shubh",   # Marathi
        "ta": "anand",   # Tamil
        "te": "anand",   # Telugu
        "bn": "maya",    # Bengali
        "pa": "shubh",   # Punjabi
        "ml": "anand",   # Malayalam
        "kn": "anand",   # Kannada
    }

    return voice_map.get(lang, "maya")


def get_language_code(lang: str) -> str:
    """
    Convert langdetect code to Sarvam language code
    """

    language_map = {
        "hi": "hi-IN",
        "en": "en-IN",
        "gu": "gu-IN",
        "mr": "mr-IN",
        "ta": "ta-IN",
        "te": "te-IN",
        "bn": "bn-IN",
        "pa": "pa-IN",
        "ml": "ml-IN",
        "kn": "kn-IN",
    }

    return language_map.get(lang, "en-IN")