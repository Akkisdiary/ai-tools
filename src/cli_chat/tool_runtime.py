"""Wires the file tools to a model invocation loop and formats tool
activity for the CLI."""
from __future__ import annotations

import json
from functools import reduce
from pathlib import Path
from typing import Any, Callable

from langchain.messages import ToolMessage
from langchain_core.messages.ai import AIMessageChunk
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

from .file_tools import TOOL_DESCRIPTIONS, build_file_tools


_TOOL_STYLE = Style.from_dict(
    {
        "tool.label": "ansibrightmagenta bold",
        "tool.arg": "ansibrightyellow",
        "tool.result": "ansibrightblue",
        "tool.error": "ansibrightred",
    }
)


def _format_args(args: dict[str, Any]) -> str:
    """Render tool arguments compactly for the CLI."""
    if not args:
        return ""
    parts = [f"{k}={json.dumps(v, ensure_ascii=False)}" for k, v in args.items()]
    return " ".join(parts)


class ToolRegistry:
    """Holds a set of tools and drives the multi-step tool-use loop.

    Use ``streamed_chat_turn`` for the streaming-with-tools flow: it
    invokes the model, executes any tool calls it returns, feeds the
    results back as ``ToolMessage``s, and streams the final assistant
    text. Multi-step tool use (model -> tool -> model -> tool -> ...)
    is handled in a loop with a safety cap.
    """

    MAX_TOOL_STEPS = 6

    def __init__(self, workdir: str | Path) -> None:
        self.workdir = Path(workdir).resolve()
        self._tools = build_file_tools(self.workdir)
        self._chat = None  # bound later via attach()
        self._by_name: dict[str, Callable[..., str]] = {t.name: t for t in self._tools}

    def attach(self, chat) -> None:
        """Bind this registry's tools onto a ChatOllama instance."""
        self._chat = chat.bind_tools(self._tools)

    @property
    def tools(self) -> list:
        return list(self._tools)

    def _print_call(self, name: str, args: dict[str, Any]) -> None:
        desc = TOOL_DESCRIPTIONS.get(name, "tool")
        print_formatted_text(
            FormattedText(
                [
                    ("class:tool.label", f"\n> \U0001f527 {desc}"),
                    ("", "  "),
                    ("class:tool.arg", _format_args(args)),
                ]
            ),
            style=_TOOL_STYLE,
        )

    def _print_result(self, content: str) -> None:
        is_error = content.startswith("error:")
        snippet = content if len(content) <= 400 else content[:400] + "\n... (truncated)"
        style_class = "class:tool.error" if is_error else "class:tool.result"
        print_formatted_text(
            FormattedText([(style_class, f"   \u2192 {snippet}")]),
            style=_TOOL_STYLE,
        )

    def _execute(self, tool_call: dict[str, Any]) -> ToolMessage:
        """Run one tool call and return a ToolMessage for the model."""
        name = tool_call["name"]
        args = tool_call.get("args", {})
        tool = self._by_name.get(name)
        if tool is None:
            result = f"error: unknown tool '{name}'"
        else:
            try:
                result = tool.invoke(args)
            except Exception as exc:  # noqa: BLE001
                result = f"error: {type(exc).__name__}: {exc}"
        return ToolMessage(content=result, tool_call_id=tool_call["id"])

    def _extract_text(self, message) -> str:
        content = getattr(message, "content", "")
        return content if isinstance(content, str) else str(content)

    def _extract_tokens(self, message) -> int | None:
        meta = getattr(message, "usage_metadata", None)
        if not meta:
            return None
        return meta.get("total_tokens")

    def run_turn(self, messages: list) -> tuple[list, str, int | None]:
        """Run a single chat turn with tool support.

        Returns ``(messages, full_assistant_text, total_tokens)``.

        The streaming UX is preserved: the first response is streamed
        chunk by chunk. If it contains tool calls, those are executed
        (with their results printed) and fed back into the model. The
        loop continues until the model produces a text-only reply or
        ``MAX_TOOL_STEPS`` is reached.
        """
        assert self._chat is not None, "call attach(chat) first"
        full = ""
        tokens: int | None = None

        # --- Step 1: stream the first response. ---
        chunks: list[AIMessageChunk] = []
        for chunk in self._chat.stream(messages):
            chunks.append(chunk)
            if chunk.content:
                print(chunk.content, end="", flush=True)
        if not chunks:
            return messages, full, tokens
        ai_message = reduce(lambda a, b: a + b, chunks)
        full = "".join(c.content for c in chunks if c.content)
        tokens = self._extract_tokens(ai_message)
        if full and not full.endswith("\n"):
            print()

        # --- Steps 2..N: tool-result follow-ups. ---
        for _ in range(self.MAX_TOOL_STEPS):
            tool_calls = getattr(ai_message, "tool_calls", None) or []
            if not tool_calls:
                break
            messages.append(ai_message)
            for call in tool_calls:
                self._print_call(call["name"], call.get("args", {}))
                result_msg = self._execute(call)
                self._print_result(result_msg.content)
                messages.append(result_msg)

            # Re-invoke with the tool results appended.
            ai_message = self._chat.invoke(messages)
            text = self._extract_text(ai_message)
            if text:
                print(text, end="", flush=True)
                full += ("\n" if full and not full.endswith("\n") else "") + text
            if tokens is None:
                tokens = self._extract_tokens(ai_message)
            if not text and not getattr(ai_message, "tool_calls", None):
                break
            if not getattr(ai_message, "tool_calls", None):
                break

        if full and not full.endswith("\n"):
            print()
        return messages, full, tokens
