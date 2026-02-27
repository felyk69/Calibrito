import os
import json

DB_FILE = "library.db"
SETTINGS_FILE = "settings.json"
DEFAULT_BOOKS_FOLDER = os.path.join(os.getcwd(), "Ebooks")
COVERS_FOLDER = os.path.join(os.getcwd(), "covers")
TRASH_FOLDER = os.path.join(os.getcwd(), "Lixeira")
KINDLE_DOCUMENTS_FOLDER = "D:/documents"

def get_books_folder():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            folder = settings.get("books_folder", "").strip()
            if folder and os.path.isdir(folder):
                return folder
        except Exception:
            pass
    return DEFAULT_BOOKS_FOLDER

def get_scanner_threads():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
            threads = settings.get("scanner_threads", 2)
            return int(threads)
        except Exception:
            pass
    return 2

os.makedirs(COVERS_FOLDER, exist_ok=True)
os.makedirs(TRASH_FOLDER, exist_ok=True)
