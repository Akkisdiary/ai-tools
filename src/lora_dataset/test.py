import os
from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

load_dotenv()


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "unavailable")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "unavailable")


def main():
    # model = ChatOpenAI(model="gpt-5.4", api_key=OPENAI_API_KEY)
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", api_key=GOOGLE_API_KEY
    )
    response = model.invoke([HumanMessage(content="Hi")])
    print(response)


if __name__ == "__main__":
    main()
