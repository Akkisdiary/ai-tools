from __future__ import annotations

import argparse
import os
from pathlib import Path

from langchain_ollama import ChatOllama
from langchain.messages import HumanMessage, AIMessage
from ollama import Client as OllamaClient
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

from .tool_runtime import ToolRegistry


def add_human_message(messages, content):
    messages.append(HumanMessage(content=content))


def add_ai_message(messages, content):
    messages.append(AIMessage(content=content))


def get_model_context_length(
    model: str, *, default: int = 8192
) -> int:
    """Look up a model's context length from the local Ollama server.

    Calls ``ollama show <model>`` and reads the ``<arch>.context_length``
    field from ``modelinfo`` (e.g. ``gemma4.context_length``,
    ``llama.context_length``). Falls back to ``default`` if the model
    isn't installed, the server is unreachable, or the field is missing.
    """
    try:
        info = OllamaClient().show(model)
    except Exception:
        return default
    arch = info.details.family
    modelinfo = info.modelinfo or {}
    key = f"{arch}.context_length"
    return int(modelinfo.get(key, default))


_STYLE = Style.from_dict(
    {
        "role": "ansibrightcyan bold",
        "colon": "ansibrightcyan",
        "user": "ansibrightgreen",
        "content": "white",
    }
)


def _print_role(role: str) -> None:
    """Print a coloured '> Role:' header that does not get overwritten
    by subsequent streaming output."""
    print_formatted_text(
        FormattedText(
            [
                ("class:role", "> "),
                ("class:role", role),
                ("class:colon", ":"),
            ]
        ),
        style=_STYLE,
    )


class CliChat:
    def __init__(
        self,
        model: str = "gemma4-128k:latest",
        workdir: str | os.PathLike[str] | None = None,
        temperature: float = 0.5,
    ) -> None:
        self._messages = []
        self._model = model
        self._temperature = temperature
        self._context_length = get_model_context_length(model)
        self.total_tokens_used = 0
        self._tools_registry = ToolRegistry(workdir or Path.cwd())
        self._tools_registry.attach(
            ChatOllama(model=model, temperature=temperature)
        )
        self._system_announced = False

    def _announce_tools(self) -> None:
        """Tell the user (once) what the model can do."""
        if self._system_announced:
            return
        self._system_announced = True
        names = ", ".join(t.name for t in self._tools_registry.tools)
        workdir = self._tools_registry.workdir
        print(f"\n> Tools: {names}")
        print(f"> Working directory: {workdir}")
        print("> Commands: /clear to reset, /tools to list, exit/quit to leave\n")

    def _handle_command(self, command: str) -> bool:
        """Process slash commands. Returns True if the turn was handled
        (no model invocation needed)."""
        cmd = command.strip().lower()
        if cmd in ("/clear", "/reset"):
            self._messages = []
            self.total_tokens_used = 0
            print("> Cleared conversation history and token counter.")
            return True
        if cmd in ("/tools",):
            for t in self._tools_registry.tools:
                print(f"  - {t.name}: {t.description.strip().splitlines()[0]}")
            return True
        if cmd in ("/help",):
            print("> Commands: /clear, /tools, /help, exit, quit")
            return True
        return False

    def _stream_assistant_response(self) -> tuple[str, int | None]:
        """Run one chat turn with tool support, streaming the final
        assistant text. Delegates the streaming + tool loop to the
        ToolRegistry."""
        messages, full, tokens = self._tools_registry.run_turn(self._messages)
        self._messages = messages
        return full, tokens

    def chat(self):
        while True:
            print("-" * 40)
            self._announce_tools()
            user_input = input("> User: ")
            stripped = user_input.strip()
            if stripped.lower() in ["exit", "quit"]:
                print("> Exiting the chat. Goodbye!")
                break
            if stripped.startswith("/") and self._handle_command(stripped):
                continue
            if not stripped:
                continue
            print("-" * 40)
            add_human_message(self._messages, user_input)
            _print_role("Assistant")
            full_response, tokens = self._stream_assistant_response()
            if full_response:
                add_ai_message(self._messages, full_response)
            if tokens:
                self.total_tokens_used += tokens
            usage_pct = (
                100 * self.total_tokens_used / self._context_length
                if self._context_length
                else 0
            )
            warning = ""
            if usage_pct >= 80:
                warning = (
                    f" \u26a0  context {usage_pct:.0f}% full"
                    " \u2014 consider /clear"
                )
            print(
                f"> [Messages: [{len(self._messages)}] "
                f"Tokens Used: {self.total_tokens_used}/"
                f"{self._context_length}]{warning}"
            )


def main():
    parser = argparse.ArgumentParser(
        description="Streaming CLI chat with file tools."
    )
    parser.add_argument(
        "--model",
        default="gemma4-128k:latest",
        help="Ollama model name (default: %(default)s).",
    )
    parser.add_argument(
        "--workdir",
        default=None,
        help=(
            "Sandbox directory for file tools "
            "(default: current working directory)."
        ),
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.5,
        help="Sampling temperature (default: %(default)s).",
    )
    args = parser.parse_args()
    CliChat(
        model=args.model,
        workdir=args.workdir,
        temperature=args.temperature,
    ).chat()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n> Chat interrupted by user.")
    except Exception as e:
        print(f"> An error occurred: {e}")
