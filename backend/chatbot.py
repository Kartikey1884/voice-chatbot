"""
Chatbot module - Handles LLM interaction with Groq
"""

import os
import json
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
from prompt import build_system_prompt

env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)



class ChatBot:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        self.sessions = {}

        # Load user data
        user_data_path = Path(__file__).parent / "user_details.json"
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
            temperature=0.7,
            max_tokens=500,
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
