import os
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

load_dotenv()

from langchain_ollama import ChatOllama
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    ToolCall,
)
from .file_tools import build_file_tools
from pathlib import Path

from .tui_handler import renderer

BASE_DIR = os.path.dirname(__file__)


cwd = Path.cwd()
TOOLS = build_file_tools(cwd)
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


def get_sys_prompt():
    with open(os.path.join(BASE_DIR, "AGENT.md")) as f:
        return f.read().strip()


def create_agent():
    chat = ChatOllama(model="gemma4-128k:latest", temperature=0.2)
    agent = chat.bind_tools(tools=TOOLS)
    return agent


def add_human_message(messages: list, content: str) -> None:
    messages.append(HumanMessage(content))


def add_ai_message(messages: list, content: str | AIMessage) -> None:
    if isinstance(content, AIMessage):
        messages.append(content)
    else:
        messages.append(AIMessage(content))


def add_tool_message(messages: list, msg: ToolMessage) -> None:
    messages.append(msg)


def exec_tool(tool_call: ToolCall) -> ToolMessage:
    """Run one tool call and return a ToolMessage for the model."""
    tool_name = tool_call.get("name")
    tool = TOOLS_BY_NAME.get(tool_name)
    status = "error"
    if tool is None:
        result = f"error: unknown tool '{tool_name}'"
    else:
        try:
            args = tool_call.get("args", {})
            renderer.display_tool_call_info(tool_name, args)
            result = tool.invoke(args)
            status = "success"
        except Exception as e:
            result = (
                f"runtime error during execution: {type(e).__name__}: {str(e)}"
            )
    return ToolMessage(
        name=tool_name,
        content=result,
        tool_call_id=tool_call["id"],
        status=status,
    )


def react_loop(messages: list, agent):
    while True:
        if not messages:
            return
        res: AIMessage = agent.invoke(messages)
        add_ai_message(messages, res)
        yield res
        if res.tool_calls:
            for tool_call in res.tool_calls:
                yield tool_call
                tool_message = exec_tool(tool_call)
                add_tool_message(messages, tool_message)
                yield tool_message
        else:
            return


def main():
    agent = create_agent()
    messages = [SystemMessage(get_sys_prompt())]

    session = PromptSession()

    try:
        while True:
            user = session.prompt("User: ")

            if not user.strip():
                continue

            add_human_message(messages, user)
            renderer.display_user_input(user)

            for res in react_loop(messages, agent):
                if isinstance(res, AIMessage) and res.content:
                    renderer.display_ai_message(res.content)
                elif isinstance(res, ToolMessage):
                    renderer.display_tool_result(res.content)

    except KeyboardInterrupt:
        renderer.display_error("Chat interupted by user.")


if __name__ == "__main__":
    main()
