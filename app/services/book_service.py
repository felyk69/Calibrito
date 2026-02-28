import os
import shutil
import sqlite3
import hashlib
import re
import ebookmeta
import fitz  # PyMuPDF
import mobi
import xml.etree.ElementTree as ET
import threading
import queue
from app.core.config import DB_FILE, COVERS_FOLDER, VALID_EXTENSIONS, get_books_folder, get_scanner_threads
from app.core.events import notify_clients
from app.core.logger import get_logger

logger = get_logger("scanner")

def process_book(file_path, file, ext):
    """Process a single book: extract metadata, cover, and save to DB."""
    title = file
    author = "Unknown"
    cover_path = None
    try:
        if ext == '.pdf':
            with fitz.open(file_path) as doc:
                pdf_meta = doc.metadata
                if pdf_meta and pdf_meta.get('title'):
                    title = pdf_meta['title']
                else:
                    title = os.path.splitext(file)[0]
                    
                if pdf_meta and pdf_meta.get('author'):
                    author = pdf_meta['author']
                    
                title = re.sub(r'^\(.*?\)\s*', '', title)
                
                try:
                    if len(doc) > 0 and os.path.getsize(file_path) < 50 * 1024 * 1024:
                        page = doc.load_page(0)
                        zoom = 300.0 / page.rect.width
                        if zoom > 1.0: zoom = 1.0
                        
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        cover_bytes = pix.tobytes("jpeg", 80)
                        
                        pix = None
                        page = None
                        
                        cover_filename = hashlib.sha256(file_path.encode('utf-8')).hexdigest() + ".jpg"
                        cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                        with open(cover_full_path, "wb") as f:
                            f.write(cover_bytes)
                        cover_path = f"/covers/{cover_filename}"
                except Exception as e:
                    logger.warning("Failed to extract PDF cover from %s: %s", file, e)
        elif ext in ['.mobi', '.azw3']:
            logger.debug("Extracting metadata from %s file: %s", ext, file)
            temp_dir, extracted_filepath = mobi.extract(file_path)
            
            for root_dir, local_dirs, local_files in os.walk(temp_dir):
                for f_name in local_files:
                    if f_name.endswith('.opf'):
                        opf_path = os.path.join(root_dir, f_name)
                        try:
                            tree = ET.parse(opf_path)
                            root_xml = tree.getroot()
                            for elem in root_xml.iter():
                                if 'title' in elem.tag.lower() and elem.text:
                                    title = re.sub(r'[\\/*?:"<>|]', "", str(elem.text)).strip()
                                if 'creator' in elem.tag.lower() and elem.text:
                                    author = str(elem.text).strip()
                        except ET.ParseError as e:
                            logger.warning("Failed to parse OPF %s: %s", opf_path, e)
                    
                    elif f_name.lower().endswith(('.jpg', '.jpeg', '.png')) and 'cover' in f_name.lower():
                        temp_cover_path = os.path.join(root_dir, f_name)
                        if not cover_path:
                            cover_filename = hashlib.sha256(file_path.encode('utf-8')).hexdigest() + ".jpg"
                            cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                            shutil.copy(temp_cover_path, cover_full_path)
                            cover_path = f"/covers/{cover_filename}"
            
            try:
                shutil.rmtree(temp_dir)
            except OSError as e:
                logger.warning("Failed to clean temp dir %s: %s", temp_dir, e)
        else:
            meta = ebookmeta.get_metadata(file_path)
            title = meta.title if meta.title else os.path.splitext(file)[0]
            title = re.sub(r'^\(.*?\)\s*', '', title)
            author = ", ".join(meta.author_list) if meta.author_list else "Unknown"
            
            if meta.cover_image_data:
                cover_filename = hashlib.sha256(file_path.encode('utf-8')).hexdigest() + ".jpg"
                cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                with open(cover_full_path, "wb") as f:
                    f.write(meta.cover_image_data)
                cover_path = f"/covers/{cover_filename}"
            
    except Exception as e:
        logger.error("Failed to extract metadata from %s: %s", file, e)
    with sqlite3.connect(DB_FILE, timeout=10.0) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO books (title, author, file_path, file_type, cover_path, added_date)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (title, author, file_path, ext, cover_path))
        conn.commit()

def scan_books(target_folder: str = None):
    """Scan the local ebooks folder and insert new files into SQLite."""
    books_folder = target_folder if target_folder else get_books_folder()
    
    if not os.path.exists(books_folder):
        os.makedirs(books_folder, exist_ok=True)
        return

    valid_extensions = VALID_EXTENSIONS
    
    files_to_process = []

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        for root, dirs, files in os.walk(books_folder):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_extensions:
                    file_path = os.path.join(root, file)
                    cursor.execute("SELECT id FROM books WHERE file_path = ?", (file_path,))
                    if cursor.fetchone():
                        continue
                    files_to_process.append((file_path, file, ext))

    if files_to_process:
        threads_count = get_scanner_threads()
        logger.info("Processing %d new files using %d threads...", len(files_to_process), threads_count)
        
        q = queue.Queue()
        
        def worker():
            while True:
                item = q.get()
                if item is None:
                    break
                try:
                    process_book(*item)
                except Exception as e:
                    logger.error("Error processing book: %s", e)
                finally:
                    q.task_done()
                    
        threads = []
        for _ in range(threads_count):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)
            
        for item in files_to_process:
            q.put(item)
            
        q.join()
        
        for _ in range(threads_count):
            q.put(None)
