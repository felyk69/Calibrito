import os
import time
import threading
import sqlite3
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from app.core.config import DB_FILE, VALID_EXTENSIONS, get_books_folder
from app.core.events import notify_clients
from app.services.book_service import process_book
from app.core.logger import get_logger

logger = get_logger("watchdog")

global_observer = None

class BookWatchdogHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            self._schedule_process(event.src_path)
            
    def on_moved(self, event):
        if not event.is_directory:
            self._schedule_process(event.dest_path)

    def _schedule_process(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in VALID_EXTENSIONS:
            file_name = os.path.basename(file_path)
            threading.Thread(target=self._process_delayed, args=(file_path, file_name, ext), daemon=True).start()

    def _process_delayed(self, file_path, file_name, ext):
        time.sleep(2)
        prev_size = -1
        retries = 0
        from sqlite3 import OperationalError
        while True:
            try:
                size = os.path.getsize(file_path)
                if size == prev_size and size > 0:
                    break
                prev_size = size
            except FileNotFoundError:
                return
            time.sleep(1)
            retries += 1
            if retries > 60:
                break
                
        time.sleep(1)
        
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM books WHERE file_path = ?", (file_path,))
                if cursor.fetchone():
                    return
        except Exception as e:
            logger.warning("DB check failed for %s: %s", file_path, e)
                
        logger.info("Processing new e-book detected: %s", file_name)
        try:
            process_book(file_path, file_name, ext)
            notify_clients("new_book")
        except Exception as e:
            logger.error("Error processing %s: %s", file_name, e)

def start_watchdog():
    global global_observer
    books_folder = get_books_folder()
    if os.path.exists(books_folder):
        global_observer = Observer()
        global_observer.schedule(BookWatchdogHandler(), books_folder, recursive=True)
        global_observer.start()
        logger.info("Watching folder: %s", books_folder)

def restart_watchdog():
    global global_observer
    if global_observer:
        try:
            global_observer.stop()
            global_observer.join()
        except Exception as e:
            logger.warning("Error stopping watchdog observer: %s", e)
    start_watchdog()

def stop_watchdog():
    global global_observer
    if global_observer:
        try:
            global_observer.stop()
            global_observer.join(timeout=2.0)
        except Exception as e:
            logger.warning("Error stopping watchdog observer during shutdown: %s", e)
