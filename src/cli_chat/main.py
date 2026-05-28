from langchain_ollama import ChatOllama
from langchain.messages import HumanMessage, AIMessage
import json


def add_human_message(messages, content):
    messages.append(HumanMessage(content=content))


def add_ai_message(messages, content):
    messages.append(AIMessage(content=content))


class CliChat:
    def __init__(self) -> None:
        self._messages = []
        self._chat = ChatOllama(model="gemma4-51200k:latest", temperature=0.5)
        self.total_tokens_used = 0

    def chat(self):
        while True:
            print("-" * 40)
            user_input = input("> User: ")
            if user_input.lower() in ["exit", "quit"]:
                print("> Exiting the chat. Goodbye!")
                break
            print("-" * 40)
            add_human_message(self._messages, user_input)
            response = self._chat.invoke(self._messages)
            print("> Assistant:", response.content)
            add_ai_message(self._messages, response.content)
            self.total_tokens_used += response.usage_metadata.get(
                "total_tokens", 0
            )
            print(
                f"> [Messages: [{len(self._messages)}] Tokens Used: {self.total_tokens_used}]"
            )


def main():
    CliChat().chat()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n> Chat interrupted by user.")
    except Exception as e:
        print(f"> An error occurred: {e}")
