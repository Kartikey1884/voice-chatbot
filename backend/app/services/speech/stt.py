from __future__ import annotations

import base64
from typing import Optional

import httpx

from app.config import settings


class STTService:
    """
    If STT_API_KEY is not set, STT is disabled.
    """

    STT_URL = settings.STT_URL

    def __init__(self, http: httpx.AsyncClient) -> None:
        self.http = http
        self.enabled = bool(settings.STT_API_KEY)

    def is_enabled(self) -> bool:
        return self.enabled

    async def audio_base64_to_text(
        self,
        audio_base64: str,
        *,
        mime: str = "audio/webm",
    ) -> Optional[str]:

        if not self.enabled or not self.STT_URL:
            print("STT is not enabled - no API key or URL configured.")
            return None

        try:
            audio_bytes = base64.b64decode(audio_base64)
            print("STT audio bytes:", len(audio_bytes), "mime:", mime)
        except Exception:
            print("Failed to decode base64 audio.")
            return None

        # Sarvam supports WebM directly (REST API). No conversion required.
        clean_mime = (mime or "audio/webm").split(";")[0].strip()  # remove ;codecs=opus

        headers = {
            "api-subscription-key": settings.STT_API_KEY,
        }

        # filename extension matters sometimes for parsers
        ext = "webm"
        if "wav" in clean_mime:
            ext = "wav"
        elif "mpeg" in clean_mime or "mp3" in clean_mime:
            ext = "mp3"

        files = {
            "file": (f"voice.{ext}", audio_bytes, clean_mime),
        }

        try:
            # Use the shared client if you want, but this is fine too
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    self.STT_URL,
                    headers=headers,
                    files=files,
                )
        except Exception as e:
            print("Error while calling STT service:", e)
            return None

        if response.status_code != 200:
            # IMPORTANT: print body so you can see the real Sarvam error
            print("STT status:", response.status_code)
            print("STT response text:", response.text[:500])
            return None

        try:
            data = response.json()
        except Exception:
            print("Failed to parse STT response as JSON.")
            return None

        # Sarvam returns "transcript" on success
        if "transcript" in data:
            return data["transcript"]

        # fallback parsing
        if "text" in data:
            return data["text"]

        if "results" in data and len(data["results"]) > 0:
            return data["results"][0].get("transcript", "")

        return None