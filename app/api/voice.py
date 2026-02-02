"""
app/api/voice.py
────────────────
WebSocket handler for VOICE chat.

Full pipeline per turn:
  1. Client records mic audio with the Web Speech API (Edge STT).
  2. Browser sends the base64-encoded transcript.
  3. Server decodes & validates the transcript (speech_to_text.py).
  4. Groq streams the LLM reply token-by-token back to the client.
  5. ElevenLabs synthesises the full reply into MP3 audio.
  6. Server sends the audio base64 blob; client plays it.

Idle behaviour (timers only tick AFTER the bot finishes speaking):
  • 12 s  → gentle follow-up prompt
  • 20 s  → goodbye + session_end signal

Barge-in:
  • If the user starts speaking while the bot's audio is playing
    the client sends { "type": "user_speaking" }.  The server
    echoes back { "type": "interrupt_audio" } and resets the timers.
"""

import os
import asyncio
import random
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.services.chatbot import ChatBot
from app.services.speech_to_text import transcribe_from_payload
from app.services.text_to_speech import generate_speech
from app.core.logging import logger


async def voice_chat_websocket(
    websocket: WebSocket,
    chatbot: ChatBot,
    active_sessions: Dict[str, Dict[str, Any]],
    get_or_create_session,
):
    await websocket.accept()
    logger.info("🎤 Voice chat connection accepted")

    # ── per-connection state ──────────────────────────────────
    session_id: Optional[str] = None
    user_name = chatbot.user_data.get("userProfile", {}).get("personalInfo", {}).get("firstName", "User")

    last_bot_finish: Optional[datetime] = None
    timeout_task:    Optional[asyncio.Task] = None
    heartbeat_task:  Optional[asyncio.Task] = None
    session_active   = True
    bot_is_busy      = False
    follow_up_sent   = False
    user_is_speaking = False

    # ── idle-timeout monitor ──────────────────────────────────
    async def idle_monitor():
        """
        Runs in the background.  Checks every second whether the
        conversation has gone quiet and sends follow-up / goodbye
        messages accordingly.
        """
        nonlocal last_bot_finish, session_active, bot_is_busy, follow_up_sent, user_is_speaking

        while session_active:
            await asyncio.sleep(1)

            if bot_is_busy or user_is_speaking or last_bot_finish is None:
                continue

            idle = (datetime.now() - last_bot_finish).total_seconds()

            # ── 12 s → follow-up ────────────────────────────
            if idle >= 12 and not follow_up_sent:
                follow_up_sent = True
                bot_is_busy    = True

                text = random.choice([
                    "I'm here if you need anything else.",
                    "Let me know if you have other questions.",
                    "Take your time — I'm listening whenever you're ready.",
                ])

                try:
                    audio_b64 = await generate_speech(text, "en")
                    await websocket.send_json({"type": "audio", "text": text, "audio": audio_b64})
                    last_bot_finish = datetime.now()   # reset so goodbye timer is relative to follow-up
                    bot_is_busy = False
                except Exception as exc:
                    logger.error("❌ Follow-up TTS error: %s", exc)
                    bot_is_busy = False
                    break

            # ── 20 s after follow-up → goodbye ──────────────
            elif idle >= 20 and follow_up_sent:
                bot_is_busy = True

                text = random.choice([
                    f"Thank you for chatting, {user_name}! Feel free to reach out anytime.",
                    f"It was great talking to you, {user_name}! Have a wonderful day!",
                    f"Have a great day, {user_name}! I'm here whenever you need me.",
                ])

                try:
                    audio_b64 = await generate_speech(text, "en")
                    await websocket.send_json({"type": "audio", "text": text, "audio": audio_b64})
                    await asyncio.sleep(3)
                    await websocket.send_json({"type": "session_end"})
                    session_active = False
                    logger.info("👋 Session ended — idle timeout")
                except Exception as exc:
                    logger.error("❌ Goodbye TTS error: %s", exc)
                break   # exit monitor loop regardless

    # ── heartbeat monitor ─────────────────────────────────────
    async def heartbeat_monitor():
        nonlocal session_active
        while session_active:
            await asyncio.sleep(15)
            try:
                await websocket.send_json({"type": "heartbeat"})
            except Exception:
                session_active = False
                break

    # ── helper: reset idle state ──────────────────────────────
    def reset_idle():
        nonlocal follow_up_sent, last_bot_finish
        follow_up_sent  = False
        last_bot_finish = None

    # ── main loop ─────────────────────────────────────────────
    try:
        heartbeat_task = asyncio.create_task(heartbeat_monitor())

        while session_active:
            data        = await websocket.receive_json()
            msg_type    = data.get("type", "")

            # ============================================================
            # 👋  GREETING
            # ============================================================
            if msg_type == "greet":
                if not session_id:
                    session_id = data.get("session_id") or os.urandom(8).hex()

                session_info = get_or_create_session(session_id)
                session_info["modes_used"].add("voice")
                is_new = session_info["message_count"] == 0

                bot_is_busy = True
                reset_idle()

                text = (
                    f"Hi {user_name}! I'm ready to help. What's on your mind?"
                    if is_new else
                    f"Welcome back, {user_name}. I'm listening."
                )

                try:
                    audio_b64 = await generate_speech(text, "en")
                    await websocket.send_json({"type": "audio", "text": text, "audio": audio_b64})
                    await asyncio.sleep(5)   # breathing room before idle timer starts
                    bot_is_busy = False

                    if timeout_task is None:
                        timeout_task = asyncio.create_task(idle_monitor())
                except Exception as exc:
                    logger.error("❌ Greeting TTS error: %s", exc)
                    await websocket.send_json({"type": "error", "message": "Greeting failed — please refresh."})
                    bot_is_busy = False
                continue

            # ============================================================
            # 🎤  AUDIO (user's voice → full pipeline)
            # ============================================================
            elif msg_type == "audio":
                bot_is_busy      = True
                user_is_speaking = False
                reset_idle()

                if not session_id:
                    session_id = data.get("session_id") or os.urandom(8).hex()

                session_info = get_or_create_session(session_id)
                session_info["modes_used"].add("voice")

                # ── Step 1: decode & validate transcript ──────
                try:
                    audio_payload = data.get("audio", "")
                    if not audio_payload:
                        raise ValueError("No audio data in payload")

                    text, language = await transcribe_from_payload(audio_payload)

                except ValueError as ve:
                    logger.warning("⚠️  STT validation: %s", ve)
                    await websocket.send_json({"type": "error", "message": str(ve)})
                    bot_is_busy     = False
                    last_bot_finish = datetime.now()
                    continue
                except Exception as exc:
                    logger.error("❌ STT error: %s", exc)
                    await websocket.send_json({"type": "error", "message": "Failed to process speech. Try again."})
                    bot_is_busy     = False
                    last_bot_finish = datetime.now()
                    continue

                # Send transcript bubble to frontend
                await websocket.send_json({"type": "transcription", "text": text, "language": language})

                # ── Step 2: LLM streaming ─────────────────────
                await websocket.send_json({"type": "status", "message": "Thinking…"})

                try:
                    full_response = ""
                    async for chunk in chatbot.stream_response(text, session_id):
                        full_response += chunk
                        await websocket.send_json({"type": "text_chunk", "text": chunk})

                    await websocket.send_json({"type": "text_complete", "text": full_response})
                    session_info["message_count"] += 1

                except Exception as exc:
                    logger.error("❌ LLM error: %s", exc)
                    await websocket.send_json({"type": "error", "message": "I had trouble processing that. Try again."})
                    bot_is_busy     = False
                    last_bot_finish = datetime.now()
                    continue

                # ── Step 3: TTS ───────────────────────────────
                await websocket.send_json({"type": "status", "message": "Speaking…"})

                try:
                    # Try detected language first; fall back to English
                    try:
                        audio_b64 = await generate_speech(full_response, language)
                    except Exception:
                        logger.warning("⚠️  TTS failed for lang=%s, falling back to English", language)
                        audio_b64 = await generate_speech(full_response, "en")
                        language  = "en"

                    await websocket.send_json({
                        "type": "audio",
                        "audio": audio_b64,
                        "text": full_response,
                        "language": language,
                    })
                    bot_is_busy = False

                except Exception as exc:
                    logger.error("❌ TTS error: %s", exc)
                    # Graceful fallback: send text only so the user still sees the answer
                    await websocket.send_json({
                        "type": "text_only",
                        "text": full_response,
                        "error": "Audio generation failed",
                    })
                    bot_is_busy     = False
                    last_bot_finish = datetime.now()

            # ============================================================
            # 🏓  PING / PONG
            # ============================================================
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            # ============================================================
            # 🔊  Audio finished playing (client tells us)
            # ============================================================
            elif msg_type == "audio_finished":
                last_bot_finish = datetime.now()
                bot_is_busy     = False
                logger.info("🔊 Audio finished — idle timer starts")

            # ============================================================
            # 🎤  User started speaking (barge-in)
            # ============================================================
            elif msg_type == "user_speaking":
                user_is_speaking = True
                reset_idle()
                logger.info("🎤 User speaking — pausing timers")
                await websocket.send_json({"type": "interrupt_audio"})

            # ============================================================
            # 🛑  User stopped speaking
            # ============================================================
            elif msg_type == "user_stopped_speaking":
                user_is_speaking = False

            else:
                logger.warning("⚠️  Unknown message type: %s", msg_type)

    except WebSocketDisconnect:
        logger.info("👋 Voice chat disconnected — session: %s", session_id)
    except Exception as exc:
        logger.error("❌ Voice chat error: %s", exc)
        try:
            await websocket.send_json({"type": "error", "message": "Unexpected error. Please refresh."})
        except Exception:
            pass
    finally:
        session_active = False
        for task in (timeout_task, heartbeat_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("🧹 Voice cleanup done — session: %s", session_id)




