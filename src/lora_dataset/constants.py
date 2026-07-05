import os
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "unavailable")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "unavailable")

IMG_SUFFIXES = (
    ".png",
    ".PNG",
    ".jpg",
    ".JPG",
    ".jpeg",
    ".JPEG",
    ".webp",
    ".WEBP",
)
