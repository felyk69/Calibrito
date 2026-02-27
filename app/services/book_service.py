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
from app.core.config import DB_FILE, COVERS_FOLDER, get_books_folder, get_scanner_threads
from app.core.events import notify_clients

def process_book(file_path, file, ext):
    """Processa um único livro: extrai metadados, capa e salva no DB."""
    title = file
    author = "Desconhecido"
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
                        
                        cover_filename = hashlib.md5(file_path.encode('utf-8')).hexdigest() + ".jpg"
                        cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                        with open(cover_full_path, "wb") as f:
                            f.write(cover_bytes)
                        cover_path = f"/covers/{cover_filename}"
                except Exception:
                    pass
        elif ext in ['.mobi', '.azw3']:
            print(f"[Scanner] Analisando arquivo s/ metadados ({ext}): {file}", flush=True)
            temp_dir, extracted_filepath = mobi.extract(file_path)
            
            for root_dir, local_dirs, local_files in os.walk(temp_dir):
                for f_name in local_files:
                    if f_name.endswith('.opf'):
                        caminho_opf = os.path.join(root_dir, f_name)
                        try:
                            tree = ET.parse(caminho_opf)
                            root_xml = tree.getroot()
                            for elem in root_xml.iter():
                                if 'title' in elem.tag.lower() and elem.text:
                                    title = re.sub(r'[\\/*?:"<>|]', "", str(elem.text)).strip()
                                if 'creator' in elem.tag.lower() and elem.text:
                                    author = str(elem.text).strip()
                        except Exception:
                            pass
                    
                    elif f_name.lower().endswith(('.jpg', '.jpeg', '.png')) and 'cover' in f_name.lower():
                        caminho_capa_temp = os.path.join(root_dir, f_name)
                        if not cover_path:
                            cover_filename = hashlib.md5(file_path.encode('utf-8')).hexdigest() + ".jpg"
                            cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                            shutil.copy(caminho_capa_temp, cover_full_path)
                            cover_path = f"/covers/{cover_filename}"
            
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        else:
            meta = ebookmeta.get_metadata(file_path)
            title = meta.title if meta.title else os.path.splitext(file)[0]
            title = re.sub(r'^\(.*?\)\s*', '', title)
            author = ", ".join(meta.author_list) if meta.author_list else "Desconhecido"
            
            if meta.cover_image_data:
                cover_filename = hashlib.md5(file_path.encode('utf-8')).hexdigest() + ".jpg"
                cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                with open(cover_full_path, "wb") as f:
                    f.write(meta.cover_image_data)
                cover_path = f"/covers/{cover_filename}"
            
    except Exception as e:
        pass
    
    dir_name = os.path.dirname(file_path)
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    safe_author = re.sub(r'[<>:"/\\|?*]', '', author)
    new_filename = f"{safe_author} - {safe_title}{ext}"
    new_path = os.path.join(dir_name, new_filename)
    
    if new_path != file_path and not os.path.exists(new_path):
        try:
            os.rename(file_path, new_path)
            file_path = new_path
        except Exception:
            pass
            
    with sqlite3.connect(DB_FILE, timeout=10.0) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO books (title, author, file_path, file_type, cover_path, added_date)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (title, author, file_path, ext, cover_path))
        conn.commit()

def scan_books(target_folder: str = None):
    """Varre a pasta local de ebooks e insere novos arquivos no SQLite."""
    books_folder = target_folder if target_folder else get_books_folder()
    
    if not os.path.exists(books_folder):
        os.makedirs(books_folder, exist_ok=True)
        return

    valid_extensions = (
        '.epub', '.mobi', '.azw3', '.azw', '.kfx', 
        '.pdf', '.cbz', '.cbr', '.djvu'
    )
    
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
        print(f"[Scanner] Processando {len(files_to_process)} novos arquivos usando {threads_count} threads...", flush=True)
        
        q = queue.Queue()
        
        def worker():
            while True:
                item = q.get()
                if item is None:
                    break
                try:
                    process_book(*item)
                except Exception as e:
                    print(f"[Scanner] Erro ao processar livro {e}", flush=True)
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
