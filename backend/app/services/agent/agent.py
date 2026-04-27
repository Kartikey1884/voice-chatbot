from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List

from app.config import settings
from app.services.agent.llm import LLM
from app.services.agent.prompt import build_system_prompt
from app.services.agent.tools import ToolRegistry


def _trim_history(history: List[Dict[str, Any]], max_pairs: int = 4) -> List[Dict[str, Any]]:
    max_len = 2 * max_pairs
    if len(history) <= max_len:
        return history
    
    trimmed = history[-max_len:]
    # OpenAI requirement: messages with role 'tool' must be preceded by a message with 'tool_calls'.
    # If we trim and the first message is 'tool', it's invalid unless the preceding 'assistant' 
    # message is also included. Easiest fix is to drop leading 'tool' messages.
    while trimmed and trimmed[0].get("role") == "tool":
        trimmed = trimmed[1:]
    
    return trimmed


class Agent:
    def __init__(self, *, llm: LLM, tools: ToolRegistry) -> None:
        self.llm = llm
        self.tools = tools

    def _base_messages(self, *, user: Dict[str, Any], history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        system = {"role": "system", "content": build_system_prompt(user=user)}
        return [system] + history

    async def _run_tool_loop(
        self,
        *,
        user: Dict[str, Any],
        history: List[Dict[str, Any]],
        user_text: str,
        tool_context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Returns the full message list to use for the final answer generation."""
        history = _trim_history(history)
        messages = self._base_messages(user=user, history=history)
        messages.append({"role": "user", "content": user_text})

        tools_payload = self.tools.openai_tools()

        for _step in range(settings.LLM_MAX_TOOL_STEPS):
            resp = await self.llm.complete(messages=messages, tools=tools_payload)
            choice = resp.choices[0]
            msg = choice.message

            tool_calls = getattr(msg, "tool_calls", None)
            if tool_calls:
                messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": tool_calls})

                for tc in tool_calls:
                    fn = tc.function
                    name = fn.name
                    args_raw = fn.arguments or "{}"
                    try:
                        args = json.loads(args_raw)
                    except Exception:
                        args = {}

                    spec = self.tools.get(name)
                    if not spec:
                        tool_out = {"ok": False, "error": f"Unknown tool: {name}"}
                    else:
                        try:
                            tool_out = await spec.handler(**args, **tool_context)
                        except Exception as e:
                            tool_out = {"ok": False, "error": f"Tool {name} failed", "detail": str(e)}

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": name,
                            "content": json.dumps(tool_out, ensure_ascii=False),
                        }
                    )

                continue

            # No tools requested -> done
            messages.append({"role": "assistant", "content": msg.content or ""})
            return messages

        messages.append({"role": "assistant", "content": "I couldn't complete the request (too many tool steps)."})
        return messages

    async def stream_answer(
        self,
        *,
        user: Dict[str, Any],
        history: List[Dict[str, Any]],
        user_text: str,
        tool_context: Dict[str, Any],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Tool loop first, then stream ONLY the final answer."""

        messages = await self._run_tool_loop(user=user, history=history, user_text=user_text, tool_context=tool_context)

        # IMPORTANT:
        # Some models may still try to emit tool-call syntax during the *final* answer.
        # If we stream with tools=None, Groq/OpenAI can raise:
        # "tool call validation failed ... attempted to call tool 'X' which was not in request.tools".
        #
        # Fix: provide the tools list but force tool_choice="none" for the final streaming pass.
        tools_payload = self.tools.openai_tools()

        # If last message is already assistant final (because tool loop ended without streaming), just emit it.
        last = messages[-1]
        if last.get("role") == "assistant" and last.get("content"):
            final_text = last["content"]
            yield {"type": "final", "text": final_text, "messages_for_history": _trim_history(messages[1:])}  # drop system
            return

        # Otherwise, generate a final assistant answer without tools, streaming tokens.
        # (In practice, the tool loop above always adds an assistant message, but keep this for safety.)
        buffer: list[str] = []
        async for chunk in self.llm.stream(messages=messages, tools=tools_payload, tool_choice="none"):
            delta = chunk.choices[0].delta
            piece = getattr(delta, "content", None)
            if piece:
                buffer.append(piece)
                yield {"type": "delta", "text": piece}

        final_text = "".join(buffer)
        yield {"type": "final", "text": final_text, "messages_for_history": _trim_history(messages[1:] + [{"role": "assistant", "content": final_text}])}
