import base64
from io import BytesIO

from PIL import Image
from pathlib import Path

from constants import BASE_DIR


def resolve_path(p: str | Path):
    path = Path(p).expanduser()
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def resolve_dataset_path(p: str | Path):
    path = Path(p).expanduser()
    if path.is_absolute():
        return path
    return (BASE_DIR / "dataset" / path).resolve()


def resolve_prompt_path(p: str | Path):
    path = Path(p).expanduser()
    if path.is_absolute():
        return path
    return (BASE_DIR / "prompts" / path).resolve()


def convert_to_base64(file_path, format="PNG"):
    buffered = BytesIO()
    Image.open(file_path).save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def read_file(abs_path: str | Path):
    with open(abs_path, "r") as f:
        return f.read()


def read_image(abs_path: str | Path):
    return convert_to_base64(abs_path)
