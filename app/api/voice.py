"""
Voice chat WebSocket endpoint - FULLY CORRECTED VERSION
All fixes applied based on the issues seen in your screenshot
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional
import os
import base64
import asyncio
from datetime import datetime
import random

from app.services.chatbot import ChatBot
from app.services.speech_to_text import transcribe_audio
from app.services.text_to_speech import generate_speech
from app.core.logging import logger


async def voice_chat_websocket(websocket: WebSocket, chatbot: ChatBot, active_sessions: Dict[str, Dict[str, Any]], get_or_create_session):
    """
    WebSocket endpoint for VOICE chat with improved interaction
    Handles: Audio → STT → LLM → TTS → Audio
    SHARES SESSION with text mode
    
    FIXES APPLIED:
    - Better audio validation (500 bytes minimum instead of 100)
    - Improved transcription validation
    - More natural timeouts (12s/20s instead of 8s/10s)
    - Connection health monitoring
    - User-friendly error messages
    - Better state management
    """
    await websocket.accept()
    logger.info("🎤 Voice chat connection accepted")
    
    # Session state
    session_id: Optional[str] = None
    user_name = chatbot.user_data["userProfile"]["personalInfo"]["firstName"]
    
    # Timing and state
    last_bot_finish_time: Optional[datetime] = None
    timeout_task: Optional[asyncio.Task] = None
    connection_task: Optional[asyncio.Task] = None
    session_active = True
    bot_is_busy = False
    follow_up_sent = False
    user_is_speaking = False
    
    
    async def check_idle_timeout():
        """
        Monitor idle time and send follow-up messages
        ONLY when bot is not busy and user is not speaking
        """
        nonlocal last_bot_finish_time, session_active, bot_is_busy, follow_up_sent, user_is_speaking
        
        logger.info("⏱️ Idle timeout monitor started")
        
        while session_active:
            await asyncio.sleep(1)
            
            # Skip if bot is busy, user is speaking, or no activity yet
            if bot_is_busy or user_is_speaking or last_bot_finish_time is None:
                continue
            
            idle_seconds = (datetime.now() - last_bot_finish_time).total_seconds()
            
            # After 12 seconds (not 8), send follow-up
            if idle_seconds >= 12 and not follow_up_sent:
                follow_up_sent = True
                bot_is_busy = True
                
                logger.info(f"⏱️ Sending follow-up after {idle_seconds:.1f}s idle")
                
                # More natural, less pushy follow-up messages
                follow_up_messages = [
                    "I'm here if you need anything else.",
                    "Let me know if you have other questions.",
                    "Take your time - I'm listening whenever you're ready."
                ]
                text = random.choice(follow_up_messages)
                
                try:
                    audio_base64 = await generate_speech(text, "en")
                    await websocket.send_json({
                        "type": "audio",
                        "text": text,
                        "audio": audio_base64
                    })
                    # Reset timer after follow-up so we don't immediately goodbye
                    last_bot_finish_time = datetime.now()
                    bot_is_busy = False
                except Exception as e:
                    logger.error(f"❌ Error sending follow-up: {e}")
                    bot_is_busy = False
                    break
            
            # After 20 seconds total (not 10), and ONLY if follow-up was sent
            elif idle_seconds >= 20 and follow_up_sent:
                bot_is_busy = True
                
                logger.info(f"⏱️ Sending goodbye after {idle_seconds:.1f}s total idle")
                
                goodbye_messages = [
                    f"Thank you for chatting with me, {user_name}! Feel free to reach out anytime.",
                    f"It was great talking to you, {user_name}! Have a wonderful day!",
                    f"Have a great day, {user_name}! I'm here whenever you need me."
                ]
                
                text = random.choice(goodbye_messages)
                
                try:
                    audio_base64 = await generate_speech(text, "en")
                    await websocket.send_json({
                        "type": "audio",
                        "text": text,
                        "audio": audio_base64
                    })
                    await asyncio.sleep(3)
                    await websocket.send_json({"type": "session_end"})
                    session_active = False
                    logger.info("👋 Session ended due to inactivity")
                except Exception as e:
                    logger.error(f"❌ Error sending goodbye: {e}")
                break
    
    
    async def monitor_connection():
        """Keep WebSocket connection alive with heartbeats"""
        nonlocal session_active
        
        logger.info("💓 Connection monitor started")
        
        while session_active:
            await asyncio.sleep(15)  # Check every 15 seconds
            try:
                await websocket.send_json({"type": "heartbeat"})
            except Exception as e:
                logger.error(f"❌ Connection health check failed: {e}")
                session_active = False
                break
    
    
    def reset_idle_state():
        """Reset idle tracking when user interacts"""
        nonlocal follow_up_sent, last_bot_finish_time
        follow_up_sent = False
        last_bot_finish_time = None
        logger.debug("🔄 Idle state reset")
    
    
    try:
        # Start connection health monitoring
        connection_task = asyncio.create_task(monitor_connection())
        
        while session_active:
            data = await websocket.receive_json()
            message_type = data.get("type", "")
            
            logger.debug(f"📨 Received: {message_type}")
            
            # ========================================
            # 👋 GREETING on connection
            # ========================================
            if message_type == "greet":
                if not session_id:
                    session_id = data.get("session_id", os.urandom(8).hex())
                    logger.info(f"🆕 Session created: {session_id[:8]}...")
                
                session_info = get_or_create_session(session_id)
                session_info["modes_used"].add("voice")
                
                is_new_session = session_info["message_count"] == 0
                
                bot_is_busy = True
                reset_idle_state()
                
                if is_new_session:
                    text = f"Hi {user_name}! I'm ready to help. What's on your mind?"
                else:
                    text = f"Welcome back, {user_name}. I'm listening."
                
                logger.info(f"👋 Greeting: '{text}'")
                
                try:
                    audio_base64 = await generate_speech(text, "en")
                    await websocket.send_json({
                        "type": "audio",
                        "text": text,
                        "audio": audio_base64
                    })
                    
                    # Give user 5 seconds to think before starting idle timer
                    await asyncio.sleep(5)
                    bot_is_busy = False
                    
                    if timeout_task is None:
                        timeout_task = asyncio.create_task(check_idle_timeout())
                
                except Exception as e:
                    logger.error(f"❌ Error sending greeting: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to send greeting. Please refresh and try again."
                    })
                    bot_is_busy = False
                
                continue
            
            # ========================================
            # 🎤 USER AUDIO input
            # ========================================
            elif message_type == "audio":
                logger.info("🎤 Processing audio input")
                
                # Update state
                bot_is_busy = True
                user_is_speaking = False
                reset_idle_state()
                
                if not session_id:
                    session_id = data.get("session_id", os.urandom(8).hex())
                    logger.info(f"🆕 Session from audio: {session_id[:8]}...")
                
                session_info = get_or_create_session(session_id)
                session_info["modes_used"].add("voice")
                
                # ========================================
                # STEP 1: Validate and decode audio
                # ========================================
                try:
                    audio_data = data.get("audio", "")
                    if not audio_data:
                        raise ValueError("No audio data provided")
                    
                    audio_bytes = base64.b64decode(audio_data)
                    audio_size = len(audio_bytes)
                    
                    logger.info(f"📊 Audio size: {audio_size} bytes")
                    
                    # Better validation with helpful messages
                    if audio_size < 500:  # Increased from 100 - catches very short recordings
                        logger.warning(f"⚠️ Audio too short: {audio_size} bytes")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Recording seems short. Hold the button and speak clearly."
                        })
                        bot_is_busy = False
                        last_bot_finish_time = datetime.now()
                        continue
                    
                    if audio_size > 10_000_000:  # 10MB limit
                        logger.warning(f"⚠️ Audio too large: {audio_size} bytes")
                        await websocket.send_json({
                            "type": "error",
                            "message": "Recording too long. Keep under 1 minute."
                        })
                        bot_is_busy = False
                        last_bot_finish_time = datetime.now()
                        continue
                    
                except ValueError as ve:
                    logger.error(f"❌ Audio validation error: {ve}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid audio format. Please try recording again."
                    })
                    bot_is_busy = False
                    last_bot_finish_time = datetime.now()
                    continue
                except Exception as decode_error:
                    logger.error(f"❌ Error decoding audio: {decode_error}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to decode audio. Please try again."
                    })
                    bot_is_busy = False
                    last_bot_finish_time = datetime.now()
                    continue
                
                # ========================================
                # STEP 2: Transcribe audio
                # ========================================
                await websocket.send_json({"type": "status", "message": "Listening..."})
                
                try:
                    # Add timeout to prevent hanging
                    text, language = await asyncio.wait_for(
                        transcribe_audio(audio_bytes),
                        timeout=10.0
                    )
                    
                    # Clean transcription
                    text = text.strip() if text else ""
                    
                    # Log for debugging (helps catch "live" vs "leave" issues)
                    logger.info(f"📝 Transcribed: '{text}' | Language: {language} | Length: {len(text)}")
                    
                    # Validate transcription
                    if not text or len(text) < 2:
                        logger.warning("⚠️ Empty or very short transcription")
                        await websocket.send_json({
                            "type": "error",
                            "message": "I couldn't hear that. Please speak a bit louder."
                        })
                        bot_is_busy = False
                        last_bot_finish_time = datetime.now()
                        continue
                    
                    # Check for gibberish (same letter repeated)
                    unique_chars = len(set(text.lower().replace(" ", "")))
                    if unique_chars <= 2:
                        logger.warning(f"⚠️ Possible gibberish: '{text}'")
                        await websocket.send_json({
                            "type": "error",
                            "message": "That didn't sound clear. Could you try again?"
                        })
                        bot_is_busy = False
                        last_bot_finish_time = datetime.now()
                        continue
                    
                    # Validate and normalize language code
                    if not language or len(language) < 2:
                        language = "en"
                    language = language[:2].lower()
                    
                    logger.info(f"✅ Valid transcription: '{text}' ({language})")
                    
                    # Send transcription to frontend
                    await websocket.send_json({
                        "type": "transcription",
                        "text": text,
                        "language": language
                    })
                
                except asyncio.TimeoutError:
                    logger.error("❌ STT timeout after 10 seconds")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Speech recognition took too long. Please try again."
                    })
                    bot_is_busy = False
                    last_bot_finish_time = datetime.now()
                    continue
                    
                except Exception as transcription_error:
                    logger.error(f"❌ Transcription error: {transcription_error}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "Failed to transcribe audio. Please try speaking again."
                    })
                    bot_is_busy = False
                    last_bot_finish_time = datetime.now()
                    continue
                
                # ========================================
                # STEP 3: Get chatbot response
                # ========================================
                await websocket.send_json({"type": "status", "message": "Thinking..."})
                
                try:
                    logger.info("🤖 Getting response from chatbot...")
                    
                    # Stream text chunks to frontend
                    full_response = ""
                    chunk_count = 0
                    
                    async for chunk in chatbot.stream_response(text, session_id):
                        full_response += chunk
                        chunk_count += 1
                        await websocket.send_json({
                            "type": "text_chunk",
                            "text": chunk
                        })
                    
                    logger.info(f"✅ Response complete: {chunk_count} chunks, {len(full_response)} chars")
                    
                    # Send completion signal
                    await websocket.send_json({
                        "type": "text_complete",
                        "text": full_response
                    })
                    
                    session_info["message_count"] += 1
                
                except Exception as llm_error:
                    logger.error(f"❌ LLM error: {llm_error}")
                    await websocket.send_json({
                        "type": "error",
                        "message": "I'm having trouble processing that. Please try again."
                    })
                    bot_is_busy = False
                    last_bot_finish_time = datetime.now()
                    continue
                
                # ========================================
                # STEP 4: Generate speech
                # ========================================
                await websocket.send_json({"type": "status", "message": "Speaking..."})
                
                try:
                    logger.info(f"🔊 Generating speech ({language})...")
                    
                    # Try with detected language first
                    try:
                        audio_base64 = await generate_speech(full_response, language)
                    except Exception as tts_lang_error:
                        logger.warning(f"⚠️ TTS failed for {language}, using English: {tts_lang_error}")
                        audio_base64 = await generate_speech(full_response, "en")
                        language = "en"
                    
                    await websocket.send_json({
                        "type": "audio",
                        "audio": audio_base64,
                        "text": full_response,
                        "language": language
                    })
                    
                    bot_is_busy = False
                    logger.info(f"✅ Response sent successfully ({language})")
                
                except Exception as tts_error:
                    logger.error(f"❌ TTS error: {tts_error}")
                    # Send text-only response as fallback
                    await websocket.send_json({
                        "type": "text_only",
                        "text": full_response,
                        "error": "Could not generate audio"
                    })
                    bot_is_busy = False
                    last_bot_finish_time = datetime.now()
            
            # ========================================
            # 🏓 Ping/Pong
            # ========================================
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            # ========================================
            # 🔇 Audio finished playing
            # ========================================
            elif message_type == "audio_finished":
                last_bot_finish_time = datetime.now()
                bot_is_busy = False
                logger.info(f"🔊 Audio finished - Starting idle timer")
            
            # ========================================
            # 🎤 User started speaking
            # ========================================
            elif message_type == "user_speaking":
                user_is_speaking = True
                reset_idle_state()
                logger.info(f"🎤 User started speaking - Pausing timers")
                
                # Send interrupt signal to stop bot audio
                await websocket.send_json({"type": "interrupt_audio"})
            
            # ========================================
            # 🛑 User stopped speaking
            # ========================================
            elif message_type == "user_stopped_speaking":
                user_is_speaking = False
                logger.info(f"🛑 User stopped speaking")
            
            # ========================================
            # ❓ Unknown message type
            # ========================================
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        logger.info(f"👋 Voice chat disconnected - Session: {session_id}")
    
    except Exception as e:
        logger.error(f"❌ Voice chat error: {e}")
        import traceback
        logger.error(f"📋 Traceback:\n{traceback.format_exc()}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "An unexpected error occurred. Please refresh and try again."
            })
        except:
            pass
    
    finally:
        # ========================================
        # Cleanup all background tasks
        # ========================================
        session_active = False
        
        if timeout_task:
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass
        
        if connection_task:
            connection_task.cancel()
            try:
                await connection_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"🧹 Cleanup complete - Session: {session_id}")