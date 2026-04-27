# from __future__ import annotations

# import base64
# from typing import Optional

# from app.config import settings
# from app.services.speech.language_selector import (
#     detect_user_language,
#     get_voice_for_language,
# )

# from elevenlabs.client import ElevenLabs



# class TTSService:
#     def __init__(self) -> None:
#         self.enabled = bool(settings.TTS_API_KEY)
        
#         if self.enabled:
#             self.client = ElevenLabs(api_key=settings.TTS_API_KEY)
#         else:
#             self.client = None

#     def is_enabled(self) -> bool:
#         return self.enabled

#     def text_to_speech_base64(self, text: str) -> Optional[str]:
#         if not self.enabled or not self.client:
#             return None
        
#         lang = detect_user_language(text)
#         voice_id = get_voice_for_language(lang)

#         audio_stream = self.client.text_to_speech.convert(
#             # voice_id=settings.TTS_VOICE_ID,
#             voice_id=voice_id,
#             model_id=settings.TTS_VOICE_MODEL_ID,
#             text=text,
#         )
#         audio_bytes = b"".join(audio_stream)
#         return base64.b64encode(audio_bytes).decode("utf-8")


from __future__ import annotations

import base64
from typing import Optional

from app.config import settings
from sarvamai import AsyncSarvamAI, AudioOutput


class TTSService:

    def __init__(self) -> None:
        self.enabled = bool(settings.TTS_API_KEY)

        if self.enabled:
            self.client = AsyncSarvamAI(
                api_subscription_key=settings.TTS_API_KEY
            )
        else:
            self.client = None


    def is_enabled(self) -> bool:
        return self.enabled


    async def text_to_speech_base64(self, text: str) -> Optional[str]:

        if not self.enabled or not self.client:
            return None

        speaker = "shubh"
        lang_code = "hi-IN"

        print(f"TTS text: {text[:50]}")

        audio_bytes = await self._generate_audio(text, speaker, lang_code)

        return base64.b64encode(audio_bytes).decode("utf-8")


    async def _receive_audio(self, ws, audio_chunks):
        async for msg in ws:
            if isinstance(msg, AudioOutput):
                chunk = base64.b64decode(msg.data.audio)
                audio_chunks.append(chunk)


    async def _generate_audio(self, text: str, speaker: str, lang_code: str) -> bytes:

        import asyncio
        import time

        start = time.perf_counter()
        audio_chunks = []

        async with self.client.text_to_speech_streaming.connect(
            model=settings.TTS_VOICE_MODEL
        ) as ws:

            await ws.configure(
                target_language_code=lang_code,
                speaker=speaker
            )

            await ws.convert(text)
            await ws.flush()

            print("Text sent to TTS")

            last_audio_time = time.perf_counter()

            while True:
                try:
                    # wait for next audio message but only for 1 second
                    msg = await asyncio.wait_for(ws.recv(), timeout=1)

                    if isinstance(msg, AudioOutput):

                        chunk = base64.b64decode(msg.data.audio)
                        audio_chunks.append(chunk)

                        last_audio_time = time.perf_counter()

                except asyncio.TimeoutError:
                    # no audio for 1 second → assume finished
                    if time.perf_counter() - last_audio_time > 1:
                        break

        print("TTS time:", time.perf_counter() - start)

        return b"".join(audio_chunks)