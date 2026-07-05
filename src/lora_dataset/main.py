import argparse
import os

from dotenv import load_dotenv
from langchain.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from .utils import open_file, open_image

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "unavailable")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "unavailable")


def get_vision_response(model: BaseChatModel, img_b64: str, prompt: str):
    image_part = {
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{img_b64}",
    }
    text_part = {"type": "text", "text": prompt}
    response = model.invoke([HumanMessage(content=[image_part, text_part])])
    return response


def create_human_message(message: str, img_b64: str | None = None):
    if img_b64:
        text_part = {"type": "text", "text": message}
        img_part = {
            "type": "image_url",
            "image_url": f"data:image/jpeg;base64,{img_b64}",
        }
        return HumanMessage(content=[img_part, text_part])
    return HumanMessage(content=message)


def stream_vision_response(model: BaseChatModel, messages: list):
    response = model.stream(messages)
    return response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("img_path")
    parser.add_argument(
        "--prompt_path",
        default="prompts/PROMPT_EDIT.md",
        required=False,
    )
    args = parser.parse_args()

    # test_model = ChatOllama(model="gemma4-128k:latest", temperature=0.4)
    test_model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    # test_model = ChatOpenAI(model="gpt-5.4")

    file_path = os.path.join(BASE_DIR, args.img_path)
    output_path = os.path.join(BASE_DIR, args.img_path + ".txt")

    test_img = open_image(file_path)
    test_prompt = open_file(os.path.join(BASE_DIR, args.prompt_path))

    print("=" * 40)

    messages = [create_human_message(test_prompt, test_img)]
    stream = stream_vision_response(test_model, messages)
    full_text = ""
    for chunk in stream:
        if isinstance(chunk, AIMessageChunk):
            if hasattr(chunk, "text") and isinstance(chunk.text, str):
                print(chunk.text, end="")
                full_text += chunk.text
            elif isinstance(chunk.content, str):
                print(chunk.content, end="")
                full_text += chunk.content
            elif isinstance(chunk.content, list):
                for part in chunk.content:
                    if isinstance(part, str):
                        print(part, end="")
                        full_text += part
                    elif isinstance(part, dict) and part.get("type") == "text":
                        print(part.get("text"), end="")
                        full_text += str(part.get("text"))
                    else:
                        print("Unknown part:", part)
        else:
            print("Unknown chunk:", chunk)

    with open(output_path, "w") as f:
        f.write(full_text)

    print("\n" + "=" * 40)


def test():
    # model = ChatOpenAI(model="gpt-5.4", api_key=OPENAI_API_KEY)
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", api_key=GOOGLE_API_KEY
    )
    response = model.invoke([HumanMessage(content="Hi")])
    print(response)


def run():
    main()


if __name__ == "__main__":
    run()
