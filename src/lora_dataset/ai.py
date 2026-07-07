from langchain.messages import HumanMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk


def create_human_message(message: str, img_b64: str | None = None):
    if img_b64:
        text_part = {"type": "text", "text": message}
        img_part = {
            "type": "image_url",
            "image_url": f"data:image/jpeg;base64,{img_b64}",
        }
        return HumanMessage(content=[img_part, text_part])
    return HumanMessage(content=message)


def get_vision_response(
    model: BaseChatModel, img_b64: str, prompt: str, log: bool = True
):
    image_part = {
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{img_b64}",
    }
    text_part = {"type": "text", "text": prompt}
    messages = [HumanMessage(content=[image_part, text_part])]

    full_text = ""
    for chunk in model.stream(messages):
        if isinstance(chunk, AIMessageChunk):
            if hasattr(chunk, "text") and isinstance(chunk.text, str):
                full_text += chunk.text
                if log:
                    print(chunk.text, end="")
            elif isinstance(chunk.content, str):
                full_text += chunk.content
                if log:
                    print(chunk.content, end="")
            elif isinstance(chunk.content, list):
                for part in chunk.content:
                    if isinstance(part, str):
                        full_text += part
                        if log:
                            print(part, end="")
                    elif isinstance(part, dict) and part.get("type") == "text":
                        full_text += str(part.get("text"))
                        if log:
                            print(part.get("text"), end="")
                    else:
                        print("Unknown part:", part)
        else:
            print("Unknown chunk:", chunk)

    if log:
        print()

    return full_text
