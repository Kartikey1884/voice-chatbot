# HRMS AI Chatbot (WebSocket)

This is a **WebSocket-first** rewrite of your HRMS chatbot:
- HTTP is used only for **login/logout/me**
- All chat happens via **/ws/chat**
- Session auth works for WebSockets (signed cookie → server-side session store)
- Modular tool registry + agent loop (LLM decides which HRMS API/tool to call)
- Text mode / Voice mode
  - Voice mode returns TTS audio (ElevenLabs)
  - Voice input via STT is optional (OpenAI Whisper REST). If not configured, voice input is disabled.

## 1) Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `HRMS_BASE_URL`
- `GROQ_API_KEY`
- (optional) `ELEVENLABS_API_KEY`
- (optional) `OPENAI_API_KEY`
- (optional) `REDIS_URL` for multi-worker scaling

## 2) Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:
- http://localhost:8000/login

## 3) Scaling

For real scalability (multiple workers / multiple servers):
- set `REDIS_URL=redis://localhost:6379/0`
- run Redis (docker-compose provided)

```bash
docker compose up -d redis
```

Then run uvicorn with multiple workers:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## WebSocket protocol
Client → Server:
- `{ "type":"user", "mode":"text"|"voice", "text":"..." }`
- `{ "type":"user", "mode":"text"|"voice", "audio_base64":"...", "audio_mime":"audio/webm" }`

Server → Client:
- `ready`: `{type:"ready", user:{...}}`
- `delta`: streamed partial text
- `final`: final assistant text
- `audio`: `{type:"audio", ok:true, audio_base64:"..."}` (only when mode=voice)
- `error`

