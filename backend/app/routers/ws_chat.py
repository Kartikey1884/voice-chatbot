from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.deps import get_session_from_ws

router = APIRouter(tags=["ws"]) 


@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await ws.accept()

    try:
        sm = ws.app.state.session_manager
        sid, session = await get_session_from_ws(ws, sm)
    except Exception as e:
        # get_session_from_ws handles ws.close(4401) for session issues
        # We just need to catch the bubble-up to prevent ASGI traceback
        print(f"WS Auth failed: {e}")
        return

    user = session.get("user") or {}
    hrms_cookies = session.get("hrms_cookies") or {}
    history = session.get("history") or []

    agent = ws.app.state.agent
    tts = ws.app.state.tts
    stt = ws.app.state.stt
    hrms = ws.app.state.hrms

    await ws.send_json({"type": "ready", "user": {"name": user.get("name"), "userType": user.get("userType"), "id": user.get("id")}})

    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "ping":
                await ws.send_json({"type": "pong"})
                continue

            # if mtype != "user":
            #     await ws.send_json({"type": "error", "message": "Invalid message type"})
            #     continue
            
            # NEW: TTS on-demand for any bubble
            if mtype == "tts":
                request_id = msg.get("request_id")
                text_for_tts = (msg.get("text") or "").strip()

                if not request_id:
                    await ws.send_json({"type": "audio", "ok": False, "message": "Missing request_id."})
                    continue

                if not text_for_tts:
                    await ws.send_json({"type": "audio", "ok": False, "request_id": request_id, "message": "Empty text."})
                    continue

                if len(text_for_tts) > 2000:
                    await ws.send_json({"type": "audio", "ok": False, "request_id": request_id, "message": "Text too long for TTS."})
                    continue

                if not tts.is_enabled():
                    await ws.send_json({"type": "audio", "ok": False, "request_id": request_id, "message": "TTS is not configured on server."})
                    continue

                try:
                    audio_b64 =await tts.text_to_speech_base64(text_for_tts)
                    if audio_b64:
                        await ws.send_json({"type": "audio", "ok": True, "request_id": request_id, "audio_base64": audio_b64, "format": "mp3"})
                    else:
                        await ws.send_json({"type": "audio", "ok": False, "request_id": request_id, "message": "Failed to generate audio."})
                except Exception as e:
                    await ws.send_json({"type": "audio", "ok": False, "request_id": request_id, "message": str(e)})
                continue

            # existing user chat flow
            if mtype != "user":
                await ws.send_json({"type": "error", "message": "Invalid message type"})
                continue
            mode = (msg.get("mode") or "text").lower()
            text = (msg.get("text") or "").strip()

            # Voice input path: client can send base64 audio instead of text
            if not text and msg.get("audio_base64"):
                if not stt.is_enabled():
                    await ws.send_json({"type": "error", "message": "STT is not configured on server."})
                    continue
                audio_mime = msg.get("audio_mime") or "audio/webm"
                transcript = await stt.audio_base64_to_text(msg["audio_base64"], mime=audio_mime)
                if not transcript:
                    await ws.send_json({"type": "error", "message": "Could not transcribe audio."})
                    continue
                text = transcript.strip()
                await ws.send_json({"type": "transcript", "text": text})

            if not text:
                await ws.send_json({"type": "error", "message": "Empty message"})
                continue

            tool_context = {"hrms": hrms, "hrms_cookies": hrms_cookies}

            # Stream answer
            assistant_text_parts: list[str] = []

            try:
                async for event in agent.stream_answer(user=user, history=history, user_text=text, tool_context=tool_context):
                    if event["type"] == "delta":
                        assistant_text_parts.append(event["text"])
                        await ws.send_json({"type": "delta", "text": event["text"]})
                    elif event["type"] == "final":
                        final_text = event["text"]
                        if not assistant_text_parts:
                            assistant_text_parts.append(final_text)
                        await ws.send_json({"type": "final", "text": final_text})

                        # Update session history
                        history = event.get("messages_for_history") or history
                        session["history"] = history
                        await sm.update(sid, session)

                        # Voice output
                        # if mode == "voice":
                        #     if not tts.is_enabled():
                        #         await ws.send_json({"type": "audio", "ok": False, "message": "TTS is not configured on server."})
                        #     else:
                        #         audio_b64 = tts.text_to_speech_base64(final_text)
                        #         if audio_b64:
                        #             await ws.send_json({"type": "audio", "ok": True, "audio_base64": audio_b64, "format": "mp3"})
                        #         else:
                        #             await ws.send_json({"type": "audio", "ok": False, "message": "Failed to generate audio."})
            except Exception as e:
                # Don't kill the WS session for a single model/tool failure.
                await ws.send_json({"type": "error", "message": str(e)})
                continue

            # loop continues

    except WebSocketDisconnect:
        return
    except Exception as e:
        # Fatal: socket-level failure.
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
        return
