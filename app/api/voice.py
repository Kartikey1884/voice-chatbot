"""
Voice chat WebSocket endpoint - GOOGLE ASSISTANT STYLE
Implements natural voice interaction with:
- Continuous listening with Voice Activity Detection (VAD)
- Automatic turn-taking (no button holding)
- Barge-in support (interrupt assistant)
- Real-time transcription feedback
- Smart silence detection
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any, Optional
import os
import base64
import asyncio
from datetime import datetime
import json

from app.services.chatbot import ChatBot
from app.services.speech_to_text import transcribe_audio
from app.services.text_to_speech import generate_speech
from app.core.logging import logger


# Voice interaction states
class VoiceState:
    IDLE = "idle"                    # Not listening, waiting for activation
    LISTENING = "listening"          # Actively listening for user speech
    PROCESSING = "processing"        # Processing user input (STT + LLM)
    SPEAKING = "speaking"            # Bot is speaking
    WAITING_FOR_CONTINUATION = "waiting"  # Brief pause to see if user continues


async def voice_chat_websocket(
    websocket: WebSocket, 
    chatbot: ChatBot, 
    active_sessions: Dict[str, Dict[str, Any]], 
    get_or_create_session
):
    """
    Google Assistant-style voice interaction
    - Always listening when activated
    - Automatic speech detection
    - Natural turn-taking
    - Interrupt capability
    """
    await websocket.accept()
    logger.info("🎤 Voice chat connection established - GOOGLE ASSISTANT MODE")
    
    # ========================================
    # Session State
    # ========================================
    session_id: Optional[str] = None
    user_name = chatbot.user_data["userProfile"]["personalInfo"]["firstName"]
    
    # Voice interaction state
    current_state = VoiceState.IDLE
    last_activity_time: Optional[datetime] = None
    
    # Tasks
    listening_task: Optional[asyncio.Task] = None
    processing_task: Optional[asyncio.Task] = None
    timeout_task: Optional[asyncio.Task] = None
    
    # Session control
    session_active = True
    is_playing_audio = False
    
    # Audio buffer for continuous listening
    audio_buffer = []
    is_speech_detected = False
    speech_start_time = None
    
    
    # ========================================
    # Helper Functions
    # ========================================
    
    async def send_state_update(state: str, **kwargs):
        """Send state updates to client"""
        try:
            await websocket.send_json({
                "type": "state_change",
                "state": state,
                **kwargs
            })
            logger.debug(f"📊 State: {state}")
        except Exception as e:
            logger.error(f"❌ Failed to send state: {e}")
    
    
    async def send_interim_transcript(text: str):
        """Send real-time transcription updates"""
        try:
            await websocket.send_json({
                "type": "interim_transcript",
                "text": text
            })
        except Exception as e:
            logger.error(f"❌ Failed to send interim: {e}")
    
    
    async def monitor_session_timeout():
        """
        Auto-end session after prolonged inactivity
        - 60 seconds of total inactivity ends session
        - Resets on any user interaction
        """
        nonlocal session_active, last_activity_time
        
        logger.info("⏱️ Session timeout monitor started (60s)")
        
        while session_active:
            await asyncio.sleep(5)
            
            if last_activity_time is None:
                continue
            
            idle_seconds = (datetime.now() - last_activity_time).total_seconds()
            
            # Warning at 45 seconds
            if idle_seconds >= 45 and idle_seconds < 50:
                await websocket.send_json({
                    "type": "timeout_warning",
                    "seconds_remaining": 60 - int(idle_seconds)
                })
            
            # End session at 60 seconds
            if idle_seconds >= 60:
                logger.info(f"⏱️ Session timeout - 60s inactivity")
                await websocket.send_json({
                    "type": "session_end",
                    "reason": "timeout"
                })
                session_active = False
                break
    
    
    async def process_user_speech(audio_data: str, language_hint: str = None):
        """
        Process user speech through the pipeline:
        1. Speech-to-Text
        2. LLM Response
        3. Text-to-Speech
        """
        nonlocal current_state, last_activity_time
        
        current_state = VoiceState.PROCESSING
        await send_state_update("processing", message="Transcribing...")
        
        try:
            # ========================================
            # STEP 1: Speech-to-Text
            # ========================================
            logger.info("🎤 Starting transcription...")
            
            audio_bytes = base64.b64decode(audio_data)
            audio_size = len(audio_bytes)
            
            logger.info(f"📊 Audio: {audio_size} bytes")
            
            if audio_size < 1000:  # Minimum viable audio
                logger.warning(f"⚠️ Audio too short: {audio_size} bytes")
                await websocket.send_json({
                    "type": "error",
                    "message": "Audio too short. Please speak longer."
                })
                current_state = VoiceState.LISTENING
                await send_state_update("listening")
                return
            
            # Transcribe with timeout
            try:
                text, detected_language = await asyncio.wait_for(
                    transcribe_audio(audio_bytes),
                    timeout=30.0
                )
            except asyncio.TimeoutError:
                logger.error("❌ STT timeout")
                await websocket.send_json({
                    "type": "error",
                    "message": "Transcription timed out. Please try again."
                })
                current_state = VoiceState.LISTENING
                await send_state_update("listening")
                return
            
            if not text or len(text.strip()) < 2:
                logger.warning(f"⚠️ Empty transcription")
                await websocket.send_json({
                    "type": "error",
                    "message": "Couldn't understand. Please try again."
                })
                current_state = VoiceState.LISTENING
                await send_state_update("listening")
                return
            
            logger.info(f"✅ Transcribed: '{text}' ({detected_language})")
            
            # Send final transcription to client
            await websocket.send_json({
                "type": "transcription",
                "text": text,
                "language": detected_language,
                "is_final": True
            })
            
            # Update session
            if session_id:
                session_info = get_or_create_session(session_id)
                session_info["message_count"] += 1
            
            # ========================================
            # STEP 2: Get LLM Response
            # ========================================
            await send_state_update("thinking", message="Thinking...")
            logger.info("🤖 Getting AI response...")
            
            full_response = ""
            chunk_count = 0
            
            try:
                async for chunk in chatbot.stream_response(text, session_id):
                    full_response += chunk
                    chunk_count += 1
                    
                    # Send streaming text to client
                    await websocket.send_json({
                        "type": "text_chunk",
                        "text": chunk
                    })
                
                logger.info(f"✅ Response: {chunk_count} chunks, {len(full_response)} chars")
                
                await websocket.send_json({
                    "type": "text_complete",
                    "text": full_response
                })
                
            except Exception as llm_error:
                logger.error(f"❌ LLM error: {llm_error}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Error generating response. Please try again."
                })
                current_state = VoiceState.LISTENING
                await send_state_update("listening")
                return
            
            # ========================================
            # STEP 3: Text-to-Speech
            # ========================================
            current_state = VoiceState.SPEAKING
            await send_state_update("speaking", message="Speaking...")
            logger.info(f"🔊 Generating speech...")
            
            try:
                # Use detected language or fallback to English
                tts_language = detected_language if detected_language else "en"
                
                try:
                    audio_base64 = await generate_speech(full_response, tts_language)
                except Exception as tts_lang_error:
                    logger.warning(f"⚠️ TTS failed for {tts_language}, using English")
                    audio_base64 = await generate_speech(full_response, "en")
                    tts_language = "en"
                
                # Send audio to client
                await websocket.send_json({
                    "type": "audio_response",
                    "audio": audio_base64,
                    "text": full_response,
                    "language": tts_language
                })
                
                logger.info(f"✅ Audio sent ({tts_language})")
                
            except Exception as tts_error:
                logger.error(f"❌ TTS error: {tts_error}")
                # Still send text even if audio fails
                await websocket.send_json({
                    "type": "text_only",
                    "text": full_response,
                    "error": "Audio generation failed"
                })
            
            # Bot will transition to LISTENING after audio finishes
            # (client sends "audio_playback_finished" event)
            
        except Exception as e:
            logger.error(f"❌ Processing error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            await websocket.send_json({
                "type": "error",
                "message": "Processing error. Please try again."
            })
            
            current_state = VoiceState.LISTENING
            await send_state_update("listening")
    
    
    # ========================================
    # WebSocket Message Handler
    # ========================================
    
    try:
        # Start session timeout monitor
        timeout_task = asyncio.create_task(monitor_session_timeout())
        
        while session_active:
            data = await websocket.receive_json()
            message_type = data.get("type", "")
            
            logger.debug(f"📨 Received: {message_type} (state: {current_state})")
            
            # ========================================
            # ACTIVATION / GREETING
            # ========================================
            if message_type == "activate":
                if not session_id:
                    session_id = data.get("session_id", os.urandom(8).hex())
                    logger.info(f"🆕 Session: {session_id[:8]}...")
                
                session_info = get_or_create_session(session_id)
                session_info["modes_used"].add("voice")
                
                is_new_session = session_info["message_count"] == 0
                
                # Send greeting
                if is_new_session:
                    greeting = f"Hi {user_name}! I'm listening. How can I help you?"
                else:
                    greeting = f"I'm listening, {user_name}."
                
                logger.info(f"👋 Greeting: '{greeting}'")
                
                current_state = VoiceState.SPEAKING
                await send_state_update("speaking", message=greeting)
                
                try:
                    audio_base64 = await generate_speech(greeting, "en")
                    await websocket.send_json({
                        "type": "audio_response",
                        "text": greeting,
                        "audio": audio_base64
                    })
                except Exception as e:
                    logger.error(f"❌ Greeting TTS error: {e}")
                    await websocket.send_json({
                        "type": "text_only",
                        "text": greeting
                    })
                
                last_activity_time = datetime.now()
            
            # ========================================
            # AUDIO PLAYBACK FINISHED
            # ========================================
            elif message_type == "audio_playback_finished":
                logger.info("🔊 Audio playback finished")
                
                # Transition to listening state
                current_state = VoiceState.LISTENING
                await send_state_update("listening", message="I'm listening...")
                
                last_activity_time = datetime.now()
            
            # ========================================
            # SPEECH DETECTED (from client VAD)
            # ========================================
            elif message_type == "speech_detected":
                logger.info("🎤 Speech detected")
                
                # If bot is speaking, allow barge-in
                if current_state == VoiceState.SPEAKING:
                    logger.info("⚡ Barge-in! Interrupting bot")
                    await websocket.send_json({
                        "type": "interrupt_playback"
                    })
                
                current_state = VoiceState.LISTENING
                await send_state_update("listening", message="Listening...")
                
                last_activity_time = datetime.now()
            
            # ========================================
            # SPEECH ENDED (from client VAD)
            # ========================================
            elif message_type == "speech_ended":
                logger.info("🛑 Speech ended, waiting for audio...")
                await send_state_update("waiting", message="Processing...")
            
            # ========================================
            # USER AUDIO INPUT
            # ========================================
            elif message_type == "audio":
                logger.info("🎤 Processing user audio")
                
                if current_state == VoiceState.PROCESSING:
                    logger.warning("⚠️ Already processing, ignoring new audio")
                    continue
                
                audio_data = data.get("audio", "")
                language_hint = data.get("language_hint", None)
                
                if not audio_data:
                    logger.warning("⚠️ No audio data received")
                    continue
                
                # Process in background
                asyncio.create_task(process_user_speech(audio_data, language_hint))
                
                last_activity_time = datetime.now()
            
            # ========================================
            # INTERIM TRANSCRIPTION (for real-time feedback)
            # ========================================
            elif message_type == "interim_audio":
                # For real-time transcription display (optional feature)
                # This would require streaming STT, which is more complex
                pass
            
            # ========================================
            # MANUAL STOP (user stops manually)
            # ========================================
            elif message_type == "stop_listening":
                logger.info("🛑 User stopped manually")
                
                if current_state == VoiceState.LISTENING:
                    current_state = VoiceState.IDLE
                    await send_state_update("idle", message="Stopped listening")
            
            # ========================================
            # REACTIVATE (wake up after idle)
            # ========================================
            elif message_type == "wake_up":
                logger.info("👂 Reactivating listening")
                
                current_state = VoiceState.LISTENING
                await send_state_update("listening", message="I'm listening...")
                
                last_activity_time = datetime.now()
            
            # ========================================
            # BARGE-IN (interrupt bot)
            # ========================================
            elif message_type == "barge_in":
                logger.info("⚡ Barge-in requested")
                
                if current_state == VoiceState.SPEAKING:
                    await websocket.send_json({
                        "type": "interrupt_playback"
                    })
                    
                    current_state = VoiceState.LISTENING
                    await send_state_update("listening", message="I'm listening...")
                
                last_activity_time = datetime.now()
            
            # ========================================
            # HEARTBEAT
            # ========================================
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            # ========================================
            # END SESSION
            # ========================================
            elif message_type == "end_session":
                logger.info("🛑 User ended session")
                await websocket.send_json({
                    "type": "session_end",
                    "reason": "user_request"
                })
                session_active = False
                break
            
            # ========================================
            # UNKNOWN MESSAGE
            # ========================================
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
    
    except WebSocketDisconnect:
        logger.info(f"👋 Client disconnected - Session: {session_id}")
    
    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Connection error. Please refresh."
            })
        except:
            pass
    
    finally:
        # ========================================
        # Cleanup
        # ========================================
        session_active = False
        
        if timeout_task:
            timeout_task.cancel()
            try:
                await timeout_task
            except asyncio.CancelledError:
                pass
        
        if listening_task:
            listening_task.cancel()
            try:
                await listening_task
            except asyncio.CancelledError:
                pass
        
        if processing_task:
            processing_task.cancel()
            try:
                await processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"🧹 Session cleanup complete - {session_id}")