from __future__ import annotations
from typing import Any, Dict, List, Optional
from groq import Groq
from app.config import GROQ_API_KEY, GROQ_MODEL

class GroqLLM:
    def __init__(self) -> None:
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = GROQ_MODEL  # e.g. llama-3.3-70b-versatile

    def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[list] = None,
        tool_choice: Optional[str] = None,
    ):
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
        }

        # Only send tools/tool_choice if tools are provided
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"   # ✅ must be "auto"/"required"/"none"
        else:
            # Ensure Groq doesn't see any tool_choice when no tools
            # (alternatively: kwargs["tool_choice"] = "none")
            pass

        return self.client.chat.completions.create(**kwargs)
