import base64
from io import BytesIO

from PIL import Image


def convert_to_base64(file_path, format="JPEG"):
    """
    Convert PIL images to Base64 encoded strings

    :param file_path: Path to the image file
    :param format: Image format for saving (default is JPEG)
    :return: Re-sized Base64 string
    """
    buffered = BytesIO()
    Image.open(file_path).save(buffered, format=format)
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return img_str
