import json
import os
import sqlite3
import threading

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import SETTINGS_FILE, get_books_folder, get_scanner_threads
from app.core.database import get_db
from app.core.logger import get_logger
from app.models.schemas import (
    ProfileCreateRequest,
    ProfileModel,
    ReadingProgressModel,
    ReadingProgressRequest,
    SettingsRequest,
    StartScanRequest,
)
from app.services.book_service import scan_books
from app.services.device_service import detect_device
from app.services.watchdog_service import restart_watchdog

logger = get_logger("routes.misc")

router = APIRouter(prefix="/api/v1", tags=["Misc"])


@router.get("/detect-device")
def detect_device_route():
    return detect_device()


@router.get("/folders")
def list_folders(path: str = ""):
    import string

    try:
        if not path or path == "/":
            drives = []
            for d in string.ascii_uppercase:
                drive_path = f"{d}:\\"
                if os.path.exists(drive_path):
                    drives.append({"name": drive_path, "path": drive_path.replace("\\", "/")})
            return {"current_path": "", "parent_path": "", "folders": drives}

        path = os.path.abspath(path)
        if not os.path.isdir(path):
            raise HTTPException(status_code=400, detail="Caminho inválido")

        folders = []
        try:
            for entry in os.scandir(path):
                if entry.is_dir() and not entry.name.startswith("$") and not entry.name.startswith("."):
                    folders.append({"name": entry.name, "path": entry.path.replace("\\", "/")})
        except PermissionError:
            pass

        folders.sort(key=lambda x: x["name"].lower())
        parent_path = os.path.dirname(path)
        if parent_path == path:  # root
            parent_path = ""

        return {
            "current_path": path.replace("\\", "/"),
            "parent_path": parent_path.replace("\\", "/"),
            "folders": folders,
        }
    except Exception as e:
        logger.error(f"Erro ao listar pastas: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/settings")
def get_settings(db: sqlite3.Connection = Depends(get_db)):
    return {"books_folder": get_books_folder(), "scanner_threads": get_scanner_threads()}


@router.put("/settings")
def save_settings(req: SettingsRequest, db: sqlite3.Connection = Depends(get_db)):
    if not os.path.exists(req.books_folder) or not os.path.isdir(req.books_folder):
        raise HTTPException(status_code=400, detail="A pasta especificada não existe ou é inválida.")

    settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                settings = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read existing settings: %s", e)

    settings["books_folder"] = req.books_folder
    settings["scanner_threads"] = req.scanner_threads

    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)

    if req.rescan:
        threading.Thread(target=scan_books, daemon=True).start()
        restart_watchdog()
        return {"status": "success", "message": "Settings updated and library rescanned."}
    else:
        return {"status": "success", "message": "Configurações atualizadas."}


@router.post("/start-scan")
def start_scan(req: StartScanRequest):
    threading.Thread(target=scan_books, args=(req.folder_path,), daemon=True).start()
    return {"status": "success", "message": "Scan started in background."}


@router.get("/profiles", response_model=list[ProfileModel])
def get_profiles(db: sqlite3.Connection = Depends(get_db)):
    conn = db
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles ORDER BY id ASC")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@router.post("/profiles", response_model=ProfileModel)
def create_profile(req: ProfileCreateRequest, db: sqlite3.Connection = Depends(get_db)):
    conn = db
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO profiles (name, avatar) VALUES (?, ?)", (req.name, req.avatar))
        conn.commit()
        profile_id = cursor.lastrowid
        return {"id": profile_id, "name": req.name, "avatar": req.avatar}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Um perfil com este nome já existe.") from None


@router.get("/profiles/{profile_id}/progress", response_model=list[ReadingProgressModel])
def get_reading_progress(profile_id: int, db: sqlite3.Connection = Depends(get_db)):
    conn = db
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reading_progress WHERE profile_id = ?", (profile_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@router.get("/books/{book_id}/progress")
def get_book_progress(book_id: int, profile_id: int = 1, db: sqlite3.Connection = Depends(get_db)):
    conn = db
    cursor = conn.cursor()
    cursor.execute(
        "SELECT cfi_location, progress_percent FROM reading_progress WHERE book_id = ? AND profile_id = ?",
        (book_id, profile_id),
    )
    row = cursor.fetchone()
    if row:
        return {"cfi_location": row[0], "progress_percent": row[1]}
    return {"cfi_location": None, "progress_percent": None}


@router.post("/books/{book_id}/progress")
def save_book_progress(
    book_id: int, req: ReadingProgressRequest, profile_id: int = 1, db: sqlite3.Connection = Depends(get_db)
):
    conn = db
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO reading_progress (profile_id, book_id, cfi_location, progress_percent, last_read)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(profile_id, book_id) DO UPDATE SET
        cfi_location=excluded.cfi_location,
        progress_percent=excluded.progress_percent,
        last_read=CURRENT_TIMESTAMP
    """,
        (profile_id, book_id, req.cfi_location, req.progress_percent),
    )
    conn.commit()
    return {"status": "success"}
