"""
app/services/chatbot.py
───────────────────────
Owns the Groq client and per-session conversation history.
Exposes a single async generator  stream_response()  that
the WebSocket handlers iterate over.

History is capped at the last 10 exchanges to keep token
usage reasonable while still giving the LLM useful context.
"""

import json
from groq import Groq

from app.core.config import settings
from app.core.logging import logger
from app.data.prompts import load_user_data, build_system_prompt


class ChatBot:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model  = settings.LLM_MODEL

        # per-session history:  { session_id: [{"role": ..., "content": ...}, …] }
        self.sessions: dict[str, list[dict]] = {}

        # Load employee data once and build the system prompt
        self.user_data     = load_user_data()
        self.system_prompt = build_system_prompt(self.user_data)

        logger.info("✅ ChatBot initialised — model: %s", self.model)

    # ── streaming response ────────────────────────────────────

    async def stream_response(self, message: str, session_id: str):
        """
        Async generator.  Yields text tokens one at a time.
        Appends both the user message and the full assistant reply
        to the session history after streaming completes.
        """
        # Build messages list: system prompt + recent history + new user turn
        messages = [{"role": "system", "content": self.system_prompt}]

        history = self.sessions.get(session_id, [])
        messages.extend(history[-10:])          # last 10 turns for context
        messages.append({"role": "user", "content": message})

        # Groq streaming call (synchronous SDK, but the generator is consumed
        # inside an async handler so the event loop stays responsive)
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            stream=True,
        )

        full_response = ""
        for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                full_response += token
                yield token

        # Persist both turns so future messages have context
        self.sessions.setdefault(session_id, []).extend([
            {"role": "user",      "content": message},
            {"role": "assistant", "content": full_response},
        ])

        logger.info("💬 [%s] assistant replied (%d chars)", session_id[:8], len(full_response))

    # ── session management ────────────────────────────────────

    def clear_session(self, session_id: str):
        """Wipe history for a session (e.g. when the user clicks Clear)."""
        self.sessions.pop(session_id, None)
        logger.info("🗑️  Session cleared: %s", session_id[:8])
