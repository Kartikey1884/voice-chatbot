# Voice Chatbot - Real-time ChatGPT-style Assistant

A real-time voice and text chatbot with WebSocket support, powered by Groq LLM, Faster Whisper (STT), and Edge TTS.

## Features

- 🎤 **Voice Mode**: Real-time voice conversation with auto-silence detection
- 💬 **Text Mode**: Streaming text responses
- 🔄 **Shared Sessions**: Conversation history persists across mode switches
- 🌍 **Multi-language**: Auto-detects and responds in user's language
- ⚡ **Fast**: Powered by Groq's ultra-fast LLM

## Project Structure

```
voice_chatbot/
│
├── app/
│   ├── main.py                 # FastAPI app entry
│   │
│   ├── api/                    # All route files
│   │   ├── chat.py            # Text chat routes
│   │   └── voice.py           # Voice chat routes
│   │
│   ├── core/                   # Config & system setup
│   │   ├── config.py           # env loader
│   │   └── logging.py          # Logging setup
│   │
│   ├── services/               # Business logic
│   │   ├── chatbot.py
│   │   ├── speech_to_text.py
│   │   └── text_to_speech.py
│   │
│   ├── static/                 # CSS, JS files
│   │   ├── style.css
│   │   └── script.js
│   │
│   ├── templates/              # HTML pages
│   │   └── index.html
│   │
│   └── data/                   # JSON, data files
│       ├── user_details.json
│       └── prompts.py
│
├── logs/                       # App logs
│
├── .env                        # Secrets
├── requirements.txt
└── README.md
```

## Installation

1. **Clone the repository** (if applicable)

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
Create a `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
HOST=0.0.0.0
PORT=8000
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=500
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
```

## Running the Application

### Option 1: Using uvicorn directly (Recommended)

From the project root directory:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

With custom host/port:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Option 2: Using the run script

```bash
python run.py
```

### Option 3: Using Python module

```bash
python -m app.main
```

## Usage

1. **Start the server** using one of the methods above

2. **Open your browser** and navigate to:
   ```
   http://localhost:8000
   ```

3. **Text Mode**:
   - Starts automatically when page loads
   - Type your message and press Enter or click Send
   - Responses stream in real-time

4. **Voice Mode**:
   - Click the "🎤 Voice" button
   - Allow microphone access when prompted
   - Bot will greet you and start listening automatically
   - Speak naturally - recording stops after 1 second of silence
   - Bot responds with both text and audio

## API Endpoints

- `GET /` - Main application page
- `GET /health` - Health check endpoint
- `GET /session/{session_id}` - Get session information
- `DELETE /session/{session_id}` - Clear a session
- `WebSocket /ws/text` - Text chat WebSocket
- `WebSocket /ws/voice` - Voice chat WebSocket

## Development

### Running in Development Mode

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables auto-reload on code changes.

### Logs

Application logs are stored in the `logs/` directory with daily rotation.

## Configuration

All configuration is managed through environment variables in `.env` file. See `app/core/config.py` for all available settings.

## Technologies Used

- **FastAPI** - Web framework
- **Groq** - LLM provider (Llama 3.3 70B)
- **Faster Whisper** - Speech-to-Text
- **Edge TTS** - Text-to-Speech
- **WebSockets** - Real-time communication
- **Web Audio API** - Browser audio processing

## Troubleshooting

- **Microphone not working**: Check browser permissions
- **Connection errors**: Ensure server is running on correct port
- **API errors**: Verify GROQ_API_KEY is set in `.env`
- **Audio issues**: Check browser console for errors

## License

MIT License
