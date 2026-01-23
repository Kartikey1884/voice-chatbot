"""
Main FastAPI application - Separate WebSocket endpoints for voice and text chat
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import json
import base64
from pathlib import Path
from dotenv import load_dotenv

from chatbot import ChatBot
from speech_to_text import transcribe_audio
from text_to_speech import generate_speech

# Load .env from project root (parent directory)
env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend directory
frontend_path = Path(__file__).parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Initialize chatbot
chatbot = ChatBot()

# from fastapi import Response

# @app.get("/favicon.ico", include_in_schema=False)
# async def favicon():
#     if (frontend_path / "favicon.ico").exists():
#         return FileResponse(str(frontend_path / "favicon.ico"))
#     return Response(status_code=204)



@app.websocket("/ws/text")
async def text_chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for TEXT-ONLY chat
    Handles streaming text responses from LLM
    """
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "text":
                # Initialize session
                if not session_id:
                    session_id = data.get("session_id", os.urandom(8).hex())
                
                text = data.get("text", "").strip()
                if not text:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty message"
                    })
                    continue
                
                # Stream chatbot response
                await websocket.send_json({"type": "status", "message": "Thinking..."})
                
                full_response = ""
                async for chunk in chatbot.stream_response(text, session_id):
                    full_response += chunk
                    await websocket.send_json({
                        "type": "text_chunk",
                        "text": chunk
                    })
                
                # Send completion
                await websocket.send_json({
                    "type": "text_complete",
                    "text": full_response
                })
            
            elif data["type"] == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        print(f"Text chat client disconnected - Session: {session_id}")
    except Exception as e:
        print(f"Text chat error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})


@app.websocket("/ws/voice")
async def voice_chat_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for VOICE chat
    Handles: Audio → STT → LLM → TTS → Audio
    """
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "audio":
                # Decode audio
                audio_bytes = base64.b64decode(data["audio"])
                
                # Step 1: Speech to Text
                await websocket.send_json({"type": "status", "message": "Transcribing..."})
                
                text, language = await transcribe_audio(audio_bytes)
                
                if not text or not text.strip():
                    await websocket.send_json({
                        "type": "error",
                        "message": "Could not understand audio"
                    })
                    continue
                
                # Send transcription
                await websocket.send_json({
                    "type": "transcription",
                    "text": text,
                    "language": language
                })
                
                # Step 2: Get LLM response
                await websocket.send_json({"type": "status", "message": "Thinking..."})
                
                if not session_id:
                    session_id = data.get("session_id", os.urandom(8).hex())
                
                full_response = ""
                async for chunk in chatbot.stream_response(text, session_id):
                    full_response += chunk
                    await websocket.send_json({
                        "type": "text_chunk",
                        "text": chunk
                    })
                
                # Step 3: Text to Speech
                await websocket.send_json({"type": "status", "message": "Generating voice..."})
                
                audio_base64 = await generate_speech(full_response, language)
                
                # Send audio response
                await websocket.send_json({
                    "type": "audio",
                    "audio": audio_base64,
                    "text": full_response
                })
            
            elif data["type"] == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        print(f"Voice chat client disconnected - Session: {session_id}")
    except Exception as e:
        print(f"Voice chat error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "endpoints": {
            "text_chat": "/ws/text",
            "voice_chat": "/ws/voice"
        },
        "model": "groq-llama-3.3-70b",
        "tts": "edge-tts",
        "stt": "faster-whisper"
    }


@app.get("/")
async def root():
    return FileResponse(str(frontend_path / "index.html"))


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting server...")
    print("📝 Text chat endpoint: ws://localhost:8000/ws/text")
    print("🎤 Voice chat endpoint: ws://localhost:8000/ws/voice")
    uvicorn.run(app, host="0.0.0.0", port=8000)