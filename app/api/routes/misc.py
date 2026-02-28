import os
import sqlite3
import json
import threading
from typing import List
from fastapi import APIRouter, HTTPException

from app.core.config import DB_FILE, SETTINGS_FILE, get_books_folder, get_scanner_threads
from app.models.schemas import SettingsRequest, StartScanRequest, ProfileModel, ProfileCreateRequest, ReadingProgressModel, ReadingProgressRequest
from app.services.book_service import scan_books
from app.services.device_service import detect_device
from app.services.watchdog_service import restart_watchdog
from app.core.logger import get_logger

logger = get_logger("routes.misc")

router = APIRouter(prefix="/api", tags=["Misc"])

@router.get("/detect-device")
def detect_device_route():
    return detect_device()

@router.get("/pick-folder")
def pick_folder():
    import tkinter as tk
    from tkinter import filedialog
    
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    folder_path = filedialog.askdirectory(parent=root, title="Select KOReader destination folder")
    root.destroy()
    
    if folder_path:
        return {"status": "success", "path": folder_path.replace('\\', '/')}
    else:
        raise HTTPException(status_code=400, detail="No folder selected.")

@router.get("/settings")
def get_settings():
    return {
        "books_folder": get_books_folder(),
        "scanner_threads": get_scanner_threads()
    }

@router.put("/settings")
def save_settings(req: SettingsRequest):
    if not os.path.exists(req.books_folder) or not os.path.isdir(req.books_folder):
        raise HTTPException(status_code=400, detail="The specified folder does not exist or is invalid.")
    
    settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read existing settings: %s", e)
            
    settings["books_folder"] = req.books_folder
    settings["scanner_threads"] = req.scanner_threads
    
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)
        
    threading.Thread(target=scan_books, daemon=True).start()
    restart_watchdog()
    return {"status": "success", "message": "Configurações atualizadas."}

@router.post("/start-scan")
def start_scan(req: StartScanRequest):
    threading.Thread(target=scan_books, args=(req.folder_path,), daemon=True).start()
    return {"status": "success", "message": "Scan started in background."}

@router.get("/profiles", response_model=List[ProfileModel])
def get_profiles():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@router.post("/profiles", response_model=ProfileModel)
def create_profile(req: ProfileCreateRequest):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO profiles (name, avatar) VALUES (?, ?)", (req.name, req.avatar))
            conn.commit()
            profile_id = cursor.lastrowid
            return {"id": profile_id, "name": req.name, "avatar": req.avatar}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="A profile with this name already exists.")

@router.get("/profiles/{profile_id}/progress", response_model=List[ReadingProgressModel])
def get_reading_progress(profile_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reading_progress WHERE profile_id = ?", (profile_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@router.get("/books/{book_id}/progress")
def get_book_progress(book_id: int, profile_id: int = 1):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cfi_location, progress_percent FROM reading_progress WHERE book_id = ? AND profile_id = ?", (book_id, profile_id))
        row = cursor.fetchone()
        if row:
            return {"cfi_location": row[0], "progress_percent": row[1]}
        return {"cfi_location": None, "progress_percent": None}

@router.post("/books/{book_id}/progress")
def save_book_progress(book_id: int, req: ReadingProgressRequest, profile_id: int = 1):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reading_progress (profile_id, book_id, cfi_location, progress_percent, last_read)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_id, book_id) DO UPDATE SET 
            cfi_location=excluded.cfi_location,
            progress_percent=excluded.progress_percent,
            last_read=CURRENT_TIMESTAMP
        ''', (profile_id, book_id, req.cfi_location, req.progress_percent))
        conn.commit()
    return {"status": "success"}
