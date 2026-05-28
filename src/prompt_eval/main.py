import os
import logging
from langchain.messages import HumanMessage
from langchain_ollama import ChatOllama

from .utils import convert_to_base64

# Configuration
BASE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "test_cases"
)

GRADER_SYSTEM_PROMPT = (
    "You are an expert AI grader. Your task is to evaluate the quality of an AI-generated "
    "description of an image based on the provided prompt and the image itself.\n\n"
    "Criteria:\n"
    "1. Accuracy: Does the description correctly identify elements in the image?\n"
    "2. Completeness: Does it answer all parts of the user prompt?\n"
    "3. Detail: Is the description vivid and precise?\n\n"
    "Provide your evaluation in the following format:\n"
    "Score: [1-10]\n"
    "Reasons: [Detailed explanation of why this score was given]"
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def get_vision_response(model, img_b64, prompt):
    """Invokes the vision model to generate a response for a given image and prompt."""
    image_part = {
        "type": "image_url",
        "image_url": f"data:image/jpeg;base64,{img_b64}",
    }
    text_part = {"type": "text", "text": prompt}

    log.info(f"Generating response for prompt: {prompt[:50]}...")
    response = model.invoke([HumanMessage(content=[image_part, text_part])])
    return response.content


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


def main():
    # Define test cases: (image_filename, prompt)
    test_cases = [
        (
            "1.jpeg",
            "Describe the pose of the subject in detail in a single paragraph without any introductory text, headers or footers. Focus on the position of the limbs, the orientation of the body, and any notable features that contribute to the overall posture.",
        ),
    ]

    log.info("Initializing model...")
    # Using gemma4 as requested
    model = ChatOllama(model="gemma4", temperature=0.1)

    for img_name, prompt in test_cases:
        img_path = os.path.join(BASE_DIR, img_name)
        if not os.path.exists(img_path):
            log.warning(f"Image not found: {img_path}. Skipping.")
            continue

        img_b64 = convert_to_base64(img_path)
        log.info(f"Processing {img_name} with prompt: {prompt}")

        # Step 1: Generation
        response_text = get_vision_response(model, img_b64, prompt)

        # Step 2: Grading
        grade_text = get_grade(model, img_b64, prompt, response_text)

        print("\n" + "=" * 80)
        print(f"TEST CASE: {img_name} | PROMPT: {prompt}")
        print("-" * 80)
        print(f"AI RESPONSE:\n{response_text}")
        print("-" * 80)
        print(f"GRADER EVALUATION:\n{grade_text}")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
