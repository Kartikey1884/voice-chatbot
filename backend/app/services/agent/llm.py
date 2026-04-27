from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional

from app.config import settings


class LLM:
    def __init__(self) -> None:
        self.provider = settings.LLM_PROVIDER.lower()
        self.model = settings.LLM_MODEL

        if self.provider == "groq":
            if not settings.LLM_API_KEY:
                raise RuntimeError("GROQ_API_KEY is not set")
            from groq import Groq
            print("----- Using Groq LLM provider -----")
            self.client = Groq(api_key=settings.LLM_API_KEY)
        else:
            if not settings.LLM_API_KEY:
                raise RuntimeError("OPENAI_API_KEY is not set")
            from openai import OpenAI
            print('----- Using OpenAI LLM provider -----')
            self.client = OpenAI(api_key=settings.LLM_API_KEY)

    def _chat_kwargs(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]], tool_choice: str | Dict[str, Any] | None, stream: bool):
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice or "auto"
        return kwargs

    async def complete(self, *, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, tool_choice=None) -> Any:
        import anyio

        def _call():
            return self.client.chat.completions.create(**self._chat_kwargs(messages, tools, tool_choice, stream=False))

        resp = await anyio.to_thread.run_sync(_call)
        return resp

    async def stream(self, *, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, tool_choice=None) -> AsyncGenerator[Any, None]:
        import anyio

        def _iter():
            return self.client.chat.completions.create(**self._chat_kwargs(messages, tools, tool_choice, stream=True))

        stream_obj = await anyio.to_thread.run_sync(_iter)

        for chunk in stream_obj:
            yield chunk
