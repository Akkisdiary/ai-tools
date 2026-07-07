import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from .ai import get_vision_response
from .utils import read_file, read_image, resolve_path
from .constants import IMG_SUFFIXES

load_dotenv()


class PromptExistsException(Exception):
    pass


def gen_edit_prompt(
    model: BaseChatModel,
    img_path: Path,
    prompt_path: Path,
):
    if not img_path.exists():
        print(f"File does not exists {img_path}")
        return

    if not img_path.is_file():
        print(f"Not a file {img_path}")
        return

    out_path = resolve_path(str(img_path) + ".txt")

    if out_path.exists() and out_path.is_file() and out_path.stat().st_size > 0:
        raise PromptExistsException(f"Prompt exists, skipping {out_path}")

    print(f"Genrating edit prompt for {img_path}")
    img_b64 = read_image(img_path)
    prompt_str = read_file(resolve_path(prompt_path))

    full_text = get_vision_response(model, img_b64, prompt_str)

    with open(out_path, "w") as f:
        f.write(full_text)

    print(f"Prompt generated {out_path}")


def gen_file(
    model: BaseChatModel,
    img_path: Path,
    prompt_path: Path,
):
    try:
        return gen_edit_prompt(model, img_path, prompt_path)
    except PromptExistsException as e:
        print(e)


def gen_folder(model: BaseChatModel, folder_path: Path, prompt_path: Path):
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
            gen_file(model, file, prompt_path)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("data_path")
    parser.add_argument(
        "--prompt_path",
        default="prompts/PROMPT_EDIT.md",
        required=False,
    )
    args = parser.parse_args()

    model = ChatOllama(model="gemma4-128k:latest", temperature=0.4)
    # model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    # model = ChatOpenAI(model="gpt-5.4")

    data_path = resolve_path(args.path)
    prompt_path = resolve_path(args.prompt_path)

    print(f"{data_path=}")
    print(f"{prompt_path=}")

    if data_path.is_dir():
        gen_folder(model, data_path, prompt_path)
    else:
        gen_file(model, data_path, prompt_path)


if __name__ == "__main__":
    main()
