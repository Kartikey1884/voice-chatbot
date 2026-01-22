"""
Main FastAPI application - WebSocket server for voice and text chat
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import base64
from pathlib import Path
from dotenv import load_dotenv

from chatbot import ChatBot
from speech_to_text import transcribe_audio
from text_to_speech import generate_speech

load_dotenv()

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


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    WebSocket for real-time voice and text conversation
    """
    await websocket.accept()
    session_id = None
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "audio":
                # Handle voice input
                audio_bytes = base64.b64decode(data["audio"])
                
                await websocket.send_json({"type": "status", "message": "Transcribing..."})
                
                # Step 1: Speech to Text
                text, language = await transcribe_audio(audio_bytes)
                
                if not text or not text.strip():
                    await websocket.send_json({
                        "type": "error",
                        "message": "Could not understand audio"
                    })
                    continue
                
                await websocket.send_json({
                    "type": "transcription",
                    "text": text,
                    "language": language
                })
                
                # Step 2: Get chatbot response
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
                
                await websocket.send_json({
                    "type": "audio",
                    "audio": audio_base64,
                    "text": full_response
                })
            
            elif data["type"] == "text":
                # Handle text input
                if not session_id:
                    session_id = data.get("session_id", os.urandom(8).hex())
                
                text = data.get("text", "").strip()
                if not text:
                    continue
                
                # Stream chatbot response
                full_response = ""
                async for chunk in chatbot.stream_response(text, session_id):
                    full_response += chunk
                    await websocket.send_json({
                        "type": "text_chunk",
                        "text": chunk
                    })
                
                await websocket.send_json({
                    "type": "text_complete",
                    "text": full_response
                })
            
            elif data["type"] == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "model": "groq-llama-3.3-70b",
        "tts": "edge-tts",
        "stt": "faster-whisper"
    }


@app.get("/")
async def root():
    return FileResponse(str(frontend_path / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)