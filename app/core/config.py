import os
import json

from app.core.logger import get_logger

logger = get_logger("config")

DB_FILE = "library.db"
SETTINGS_FILE = "settings.json"
DEFAULT_BOOKS_FOLDER = os.path.join(os.getcwd(), "Ebooks")
COVERS_FOLDER = os.path.join(os.getcwd(), "covers")
TRASH_FOLDER = os.path.join(os.getcwd(), "Lixeira")
DEFAULT_KINDLE_FOLDER = "D:/documents"

VALID_EXTENSIONS = (
    '.epub', '.mobi', '.azw3', '.azw', '.kfx',
    '.pdf', '.cbz', '.cbr', '.djvu',
)

def get_books_folder():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            folder = settings.get("books_folder", "").strip()
            if folder and os.path.isdir(folder):
                return folder
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read settings file: %s", e)
    return DEFAULT_BOOKS_FOLDER

def get_scanner_threads():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            threads = settings.get("scanner_threads", 2)
            return int(threads)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("Failed to read scanner_threads from settings: %s", e)
    return 2

def get_kindle_folder() -> str:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            folder = settings.get("kindle_folder", "").strip()
            if folder:
                return folder
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read kindle_folder from settings: %s", e)
    return DEFAULT_KINDLE_FOLDER

os.makedirs(COVERS_FOLDER, exist_ok=True)
os.makedirs(TRASH_FOLDER, exist_ok=True)
