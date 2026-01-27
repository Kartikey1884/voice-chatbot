"""
Chatbot module - Handles LLM interaction with Groq
"""

import json
from pathlib import Path
from groq import Groq

from app.core.config import settings
from app.data.prompts import build_system_prompt


class ChatBot:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.LLM_MODEL
        self.sessions = {}

        # Load user data
        user_data_path = settings.DATA_DIR / "user_details.json"
        with open(user_data_path, "r", encoding="utf-8") as f:
            self.user_data = json.load(f)

        # Build system prompt from prompt file
        self.system_prompt = build_system_prompt(self.user_data)

    async def stream_response(self, message: str, session_id: str):
        """Stream LLM response from Groq"""

        messages = [{"role": "system", "content": self.system_prompt}]

        history = self.sessions.get(session_id, [])
        messages.extend(history[-10:])

        messages.append({"role": "user", "content": message})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            stream=True
        )

        full_response = ""

        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield content

        self.sessions.setdefault(session_id, []).extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": full_response}
        ])

    def clear_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
