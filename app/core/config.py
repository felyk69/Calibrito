import json
import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logger import get_logger

logger = get_logger("config")


class AppSettings(BaseSettings):
    db_file: str = "library.db"
    settings_file: str = "settings.json"
    books_folder: str = os.path.join(os.getcwd(), "Ebooks")
    covers_folder: str = os.path.join(os.getcwd(), "covers")
    trash_folder: str = os.path.join(os.getcwd(), "Lixeira")
    default_kindle_folder: str = "D:/documents"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


env_settings = AppSettings()

DB_FILE = env_settings.db_file
SETTINGS_FILE = env_settings.settings_file
DEFAULT_BOOKS_FOLDER = env_settings.books_folder
COVERS_FOLDER = env_settings.covers_folder
TRASH_FOLDER = env_settings.trash_folder
DEFAULT_KINDLE_FOLDER = env_settings.default_kindle_folder

VALID_EXTENSIONS = (
    ".epub",
    ".mobi",
    ".azw3",
    ".azw",
    ".kfx",
    ".pdf",
    ".cbz",
    ".cbr",
    ".djvu",
)


def get_books_folder():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
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
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                settings = json.load(f)
            threads = settings.get("scanner_threads", 2)
            return int(threads)
        except (json.JSONDecodeError, OSError, ValueError) as e:
            logger.warning("Failed to read scanner_threads from settings: %s", e)
    return 2


def get_kindle_folder() -> str:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                settings = json.load(f)
            folder = settings.get("kindle_folder", "").strip()
            if folder:
                return folder
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read kindle_folder from settings: %s", e)
    return DEFAULT_KINDLE_FOLDER


os.makedirs(COVERS_FOLDER, exist_ok=True)
os.makedirs(TRASH_FOLDER, exist_ok=True)
