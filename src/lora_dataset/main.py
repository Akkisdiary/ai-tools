import argparse
from pathlib import Path

from ai import get_vision_response
from constants import IMG_SUFFIXES
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from utils import (
    read_file,
    read_image,
    resolve_dataset_path,
    resolve_prompt_path,
)
from constants import BASE_DIR

load_dotenv()


class PromptExistsException(Exception):
    pass


def gen_edit_prompt(
    model: BaseChatModel,
    img_path: Path,
    prompt_path: Path,
    trigger_word: str | None = None,
):
    if not img_path.exists():
        print(f"File does not exists {img_path}")
        return

    if not img_path.is_file():
        print(f"Not a file {img_path}")
        return

    out_path = resolve_dataset_path(img_path).with_suffix(".txt")

    if out_path.exists() and out_path.is_file() and out_path.stat().st_size > 0:
        raise PromptExistsException(f"Prompt exists, skipping {out_path}")

    print(f"Genrating prompt for {img_path}")
    img_b64 = read_image(img_path)
    prompt_str = read_file(resolve_prompt_path(prompt_path))

    if isinstance(trigger_word, str):
        prompt_str = prompt_str.replace("{trigger_word}", trigger_word)

    full_text = get_vision_response(model, img_b64, prompt_str)

    with open(out_path, "w") as f:
        f.write(full_text)

    print(f"Prompt generated {out_path}")


def gen_file(
    model: BaseChatModel,
    img_path: Path,
    prompt_path: Path,
    trigger_word: str | None = None,
):
    try:
        return gen_edit_prompt(model, img_path, prompt_path, trigger_word)
    except PromptExistsException as e:
        print(e)


def gen_folder(
    model: BaseChatModel,
    folder_path: Path,
    prompt_path: Path,
    trigger_word: str | None = None,
):
    if not folder_path.exists():
        raise ValueError(f"Folder does not exist {folder_path}")

    print(f"Generating prompts for folder {folder_path}")
    success = failed = skipped = 0

    for file in folder_path.iterdir():
        if not file.exists() or not file.is_file():
            continue
        if file.suffix not in IMG_SUFFIXES:
            print(f"Not an image {file}")
            continue
        try:
            gen_file(model, file, prompt_path, trigger_word)
            success += 1
        except PromptExistsException as e:
            skipped += 1
            print(e)
        except Exception as e:
            print(f"Unable to gen prompt for {file}\n{e}")
            failed += 1

    print(f"{success=}")
    print(f"{failed=}")
    print(f"{skipped=}")


def get_prompt_choices():
    prompts_dir = Path(BASE_DIR) / "prompts"
    return [
        f.name
        for f in prompts_dir.iterdir()
        if f.is_file() and f.suffix in (".md", ".MD")
    ]


def main():
    prompt_choices = get_prompt_choices()
    parser = argparse.ArgumentParser()
    parser.add_argument("data_path")
    parser.add_argument(
        "--prompt_path",
        default="CHAR_LORA.md",
        required=False,
        choices=prompt_choices,
    )
    parser.add_argument(
        "--trigger_word",
        default=None,
        required=False,
    )
    args = parser.parse_args()

    model = ChatOllama(model="gemma4-128k:latest", temperature=0.4)
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    # model = ChatOpenAI(model="gpt-5.4")

    data_path = resolve_dataset_path(args.data_path)
    prompt_path = resolve_prompt_path(args.prompt_path)
    trigger_word = args.trigger_word

    print(f"{data_path=}")
    print(f"{prompt_path=}")
    print(f"{trigger_word=}")

    if data_path.is_dir():
        gen_folder(model, data_path, prompt_path, trigger_word)
    else:
        gen_file(model, data_path, prompt_path, trigger_word)


if __name__ == "__main__":
    main()
