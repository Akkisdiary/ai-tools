import argparse
import base64
import io
import os
import time
from io import BytesIO

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from PIL import Image
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def open_file(file_path):
    with open(file_path, "r") as f:
        return f.read()


def infer_pil_img_type(file_path):
    ext_to_type = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
    }
    base_name = os.path.basename(file_path)
    ext = os.path.splitext(base_name)[1].lower()
    if ext not in ext_to_type:
        raise ValueError(f"Unsupported image extension: {ext}")
    return ext_to_type[ext]


def open_image(file_path):
    buffered = BytesIO()
    Image.open(file_path).save(buffered, format=infer_pil_img_type(file_path))
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def get_chat_gemini():
    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash", api_key=os.getenv("GOOGLE_API_KEY")
    )


def describe_image(img_path: str, prompt: str):
    img_b64 = open_image(img_path)
    img_basename = os.path.basename(img_path)
    img_ext = os.path.splitext(img_basename)[1].lstrip(".").lower()
    image_part = {
        "type": "image_url",
        "image_url": f"data:image/{img_ext};base64,{img_b64}",
    }
    text_part = {"type": "text", "text": prompt}
    model = get_chat_gemini()
    response = model.invoke([HumanMessage(content=[image_part, text_part])])
    if hasattr(response, "text") and isinstance(response.text, str):
        return response.text
    if hasattr(response, "content") and isinstance(response.content, str):
        return response.content
    if hasattr(response, "content") and isinstance(response.content, list):
        content = ""
        for part in response.content:
            if part.get("type") == "text":
                content += part.get("type", "")
        return content

    raise RuntimeError(f"Unable to get content from model response: {response}")


def caption_image(img_path):
    if not os.path.exists(img_path):
        raise ValueError(f"Image path {img_path} does not exist")

    if not os.path.isfile(img_path):
        raise ValueError(f"Image path {img_path} is not a file")

    img_name = os.path.splitext(os.path.basename(img_path))[0]

    caption_path = os.path.join(os.path.dirname(img_path), img_name + ".txt")
    if os.path.exists(caption_path):
        try:
            if os.path.getsize(caption_path) > 0:
                print(f"Skipping {img_path} (caption exists)")
                return
        except OSError:
            pass

    start = time.perf_counter()
    try:
        print("Captioning image:", img_path)
        prompt = open_file(os.path.join(BASE_DIR, "prompts/CHAR_LORA.md"))
        prompt = prompt.replace("{trigger_word}", "dre4mm1a")
        caption = describe_image(img_path, prompt)
    finally:
        print("Time taken:", time.perf_counter() - start)

    print("Writing caption to file:", caption_path)
    with open(caption_path, "w") as f:
        f.write(caption)


def caption_image_dataset(image_dir):
    if not os.path.exists(image_dir):
        raise ValueError(f"Image directory {image_dir} does not exist")

    for file in os.listdir(image_dir):
        try:
            caption_image(os.path.join(image_dir, file))
        except Exception as e:
            print(f"Unable to caption image {file}: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()

    if os.path.isdir(args.path):
        caption_image_dataset(args.path)
    else:
        caption_image(args.path)


if __name__ == "__main__":
    main()
