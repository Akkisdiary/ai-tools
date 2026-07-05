import base64
import os
from io import BytesIO

from PIL import Image


def infer_pil_img_type(file_path):
    ext_to_type = {
        ".png": "PNG",
        ".jpg": "JPEG",
        ".jpeg": "JPEG",
    }
    ext = os.path.splitext(file_path)[1]
    return ext_to_type[ext]


def convert_to_base64(file_path, format="PNG"):
    buffered = BytesIO()
    Image.open(file_path).save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str


def open_image(file_path):
    # format = infer_pil_img_type(file_path)
    return convert_to_base64(file_path)


def open_file(file_path):
    with open(file_path, "r") as f:
        return f.read()
