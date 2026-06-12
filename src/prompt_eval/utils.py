import base64
from io import BytesIO

from PIL import Image


def convert_to_base64(file_path, format="PNG"):
    buffered = BytesIO()
    Image.open(file_path).save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def open_image(file_path, format="PNG"):
    return convert_to_base64(file_path, format)


def open_file(file_path):
    with open(file_path, "r") as f:
        return f.read()
