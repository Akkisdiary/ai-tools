import os

from dotenv import load_dotenv

load_dotenv()

from langchain_ollama import ChatOllama
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    ToolCall,
)

BASE_DIR = os.path.dirname(__file__)


def get_sys_prompt():
    with open(os.path.join(BASE_DIR, "src/cli_chat/AGENT.md")) as f:
        return f.read().strip()


def subtract(x: float, y: float) -> float:
    """Subtract 'x' from 'y'."""
    return y - x


def add(x: float, y: float) -> float:
    """Add 'x' and 'y'."""
    return x + y


tools = {"add": add, "subtract": subtract}


def create_chat():
    chat = ChatOllama(model="gemma4-128k:latest", temperature=0.2)
    chat = chat.bind_tools([subtract, add])
    return chat


def add_human_message(messages: list, content: str) -> None:
    messages.append(HumanMessage(content))


def add_ai_message(messages: list, content: str) -> None:
    messages.append(AIMessage(content))


def add_tool_message(messages: list, msg: ToolMessage) -> None:
    messages.append(msg)


def exec_tool(tool_call: ToolCall) -> ToolMessage:
    """Run one tool call and return a ToolMessage for the model."""
    tool_name = tool_call.get("name")
    tool = tools.get(tool_name)
    if tool is None:
        result = f"error: unknown tool '{tool_name}'"
        print(f"Tool not found: {tool_name}")
    else:
        try:
            args = tool_call.get("args", {})
            print(f"Exec tool: {tool_name}({args})")
            result = str(tool(**args))
        except Exception as exc:
            result = f"error: {type(exc).__name__}: {exc}"
    return ToolMessage(content=result, tool_call_id=tool_call["id"])


def reAct_loop(messages: list, chat):
    while True:
        if not messages:
            return
        res = chat.invoke(messages)
        yield res
        add_ai_message(messages, res.content)
        if res.tool_calls:
            for call in res.tool_calls:
                tm = exec_tool(call)
                print(f"Tool result: {tm.content}")
                add_tool_message(messages, tm)
        else:
            return


def main():
    chat = create_chat()
    messages = []
    messages.append(SystemMessage(get_sys_prompt()))

    try:
        while True:
            user = input("User: ")
            add_human_message(messages, user)
            for res in reAct_loop(messages, chat):
                print("AI:", res.content)
    except KeyboardInterrupt:
        print("\n Chat closed by user.")


if __name__ == "__main__":
    main()
