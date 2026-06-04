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
    with open(os.path.join(BASE_DIR, "AGENT.md")) as f:
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


def create_agent():
    from langchain.agents import create_agent

    agent = create_agent(
        model=ChatOllama(model="gemma4-128k:latest", temperature=0.2),
        tools=[subtract, add],
        system_prompt=get_sys_prompt(),
    )
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
    tool = tools.get(tool_name)
    status = "error"
    if tool is None:
        result = f"error: unknown tool '{tool_name}'"
    else:
        try:
            args = tool_call.get("args", {})
            print(f" - exec tool: {tool_name}({args})")
            result = str(tool(**args))
            status = "success"
        except Exception as exc:
            result = f"error: {type(exc).__name__}: {exc}"
    return ToolMessage(
        name=tool_name,
        content=result,
        tool_call_id=tool_call["id"],
        status=status,
    )


def react_loop(messages: list, chat):
    while True:
        if not messages:
            return
        res: AIMessage = chat.invoke(messages)
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
    chat = create_chat()
    messages = []
    messages.append(SystemMessage(get_sys_prompt()))

    try:
        while True:
            user = input("> User: ")
            add_human_message(messages, user)
            for res in react_loop(messages, chat):
                if isinstance(res, AIMessage) and res.content:
                    print("> AI:", res.content)
                elif isinstance(res, ToolMessage):
                    print(" - tool res:", res.content)
    except KeyboardInterrupt:
        print("\n Chat closed by user.")


if __name__ == "__main__":
    main()
