<<<<<<< Updated upstream
"""
Chatbot module - Handles LLM interaction with Groq
"""

=======
>>>>>>> Stashed changes
import json
from pathlib import Path
from groq import Groq

from app.core.config import settings
from app.data.prompts import build_system_prompt
<<<<<<< Updated upstream
=======
from app.services.tool_router import route_tool
>>>>>>> Stashed changes


class ChatBot:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.LLM_MODEL
<<<<<<< Updated upstream
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
=======

        self.sessions: dict[str, list[dict]] = {}
        self.system_prompts: dict[str, str] = {}

    # called after login
    def set_user_context(self, session_id: str, user: dict):
        self.system_prompts[session_id] = build_system_prompt(user)

    # intent guard
    def is_leave_intent(self, text: str) -> bool:
        keywords = ["leave", "leaves", "pl", "so", "sick", "holiday", "vacation", "off"]
        return any(k in text.lower() for k in keywords)

    async def stream_response(self, message: str, session_id: str, cookies: dict):

        if session_id not in self.system_prompts:
            yield "⚠️ Please login first."
            return

        messages = [{"role": "system", "content": self.system_prompts[session_id]}]
        messages.extend(self.sessions.get(session_id, [])[-10:])
        messages.append({"role": "user", "content": message})

        # ── STEP 1: get FULL response (NO streaming yet)
        response = self.client.chat.completions.create(
>>>>>>> Stashed changes
            model=self.model,
            messages=messages,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
<<<<<<< Updated upstream
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
=======
        )

        content = response.choices[0].message.content.strip()

        # ── STEP 2: try parsing tool JSON
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = None

        # ── STEP 3: TOOL CALL HANDLING
        if isinstance(parsed, dict) and parsed.get("tool") == "leave_summary":

            if not self.is_leave_intent(message):
                yield "I can check leave details only when you ask about leave."
                return

            api = route_tool(
                parsed["tool"],
                parsed["arguments"],
                cookies
            )

            if not api or api.get("STATUS") != 1:
                yield "I couldn’t fetch your leave details right now."
                return

            leave = api["DATA"][0]["leave"]
            pl = leave.get("PL", {}).get("balance", 0)
            so = leave.get("SO", {}).get("balance", 0)

            answer = (
                f"You currently have:\n"
                f"• Paid Leave (PL): {pl}\n"
                f"• Sick / Optional Leave (SO): {so}\n\n"
                f"Would you like to apply for leave? "
                f"If yes, tell me the **from date**."
            )

            yield answer

            self.sessions.setdefault(session_id, []).append(
                {"role": "assistant", "content": answer}
            )
            return

        # ── STEP 4: NORMAL CHAT → stream safely
        full = ""
        for ch in content:
            full += ch
            yield ch

        self.sessions.setdefault(session_id, []).extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": full},
        ])
>>>>>>> Stashed changes
