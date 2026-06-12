import os
from langchain.messages import HumanMessage
from langchain_core.messages import AIMessageChunk
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_ollama import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from .utils import open_image, open_file
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "unavailable")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "unavailable")

GRADER_SYSTEM_PROMPT = """
You are an expert AI grader.
Your task is to evaluate the quality of an AI-generated description of
an image based on the provided prompt and the image itself.
Criteria:
    1. Accuracy: Does the description correctly identify elements in the image?"
    2. Completeness: Does it answer all parts of the user prompt?"
    3. Detail: Is the description vivid and precise?
Provide your evaluation in the following format:
- Score: [1-10]
- Reasons: [Detailed explanation of why this score was given]
"""


def get_vision_response(model: BaseChatModel, img_b64: str, prompt: str):
    image_part = {
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{img_b64}",
    }
    text_part = {"type": "text", "text": prompt}
    response = model.invoke([HumanMessage(content=[image_part, text_part])])
    return response


def stream_vision_response(model: BaseChatModel, img_b64: str, prompt: str):
    image_part = {
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{img_b64}",
    }
    text_part = {"type": "text", "text": prompt}
    response = model.stream([HumanMessage(content=[image_part, text_part])])
    return response


def get_grade(model, img_b64, prompt, response_text):
    """Invokes the model to grade a previously generated response."""
    image_part = {
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{img_b64}",
    }

    grading_prompt = (
        f"{GRADER_SYSTEM_PROMPT}\n\n"
        f"Original Prompt: {prompt}\n"
        f"AI Generated Response: {response_text}\n\n"
        f"Please grade the response now."
    )

    text_part = {"type": "text", "text": grading_prompt}

    log.info("Grading the response...")
    grade_response = model.invoke(
        [HumanMessage(content=[image_part, text_part])]
    )
    return grade_response.content


def infer_pil_img_type(file_path):
    ext_to_type = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
    }
    ext = os.path.splitext(file_path)[1]
    return ext_to_type[ext]


def main():
    print("=" * 40)

    test_model = ChatOllama(model="gemma4", temperature=0.4)
    # test_model = ChatGoogleGenerativeAI(
    #     model="gemini-3.5-flash", api_key=GOOGLE_API_KEY
    # )

    file_path = os.path.join(BASE_DIR, "imgs/img11.jpg")
    img_type = infer_pil_img_type(file_path)

    test_img = open_image(file_path, img_type)
    test_prompt = open_file(os.path.join(BASE_DIR, "PROMPT2.md"))

    stream = stream_vision_response(test_model, test_img, test_prompt)
    for chunk in stream:
        if isinstance(chunk, AIMessageChunk):
            print(chunk.content, end="")
        else:
            print("Unknown chunk:", chunk)

    # grader_model = ChatOllama(model="gemma4", temperature=0.4)
    print("\n" + "=" * 40)


# def main():
#     # model = ChatOpenAI(model="gpt-5.4", api_key=OPENAI_API_KEY)
#     model = ChatGoogleGenerativeAI(
#         model="gemini-2.5-flash", api_key=GOOGLE_API_KEY
#     )
#     response = model.invoke([HumanMessage(content="Hi")])
#     print(response)


if __name__ == "__main__":
    main()
