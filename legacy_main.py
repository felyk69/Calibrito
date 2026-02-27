import os
import shutil
import sqlite3
import ebookmeta
import re
from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import hashlib
import fitz  # PyMuPDF
import mobi
import xml.etree.ElementTree as ET
import threading
import concurrent.futures
import asyncio
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from fastapi.responses import StreamingResponse
import requests

app = FastAPI(title="Kindle Library Manager")
templates = Jinja2Templates(directory="templates")

# Configurações do Banco de Dados e Pastas
DB_FILE = "library.db"
SETTINGS_FILE = "settings.json"
DEFAULT_BOOKS_FOLDER = os.path.join(os.getcwd(), "Ebooks")
COVERS_FOLDER = os.path.join(os.getcwd(), "covers") # Pasta onde as capas ficarão salvas
TRASH_FOLDER = os.path.join(os.getcwd(), "Lixeira") # Pasta para arquivos excluídos não-permanentemente
KINDLE_DOCUMENTS_FOLDER = "D:/documents" # Caminho padrão do Kindle (Windows).

import json

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
app.mount("/covers", StaticFiles(directory="covers"), name="covers")

class BookModel(BaseModel):
    id: int
    title: str
    author: str
    file_path: str
    file_type: str
    cover_path: Optional[str] = None
    added_date: Optional[str] = None
    series: Optional[str] = None
    volume: Optional[float] = None
    synopsis: Optional[str] = None
    publisher: Optional[str] = None
    publish_year: Optional[int] = None

class SendBookRequest(BaseModel):
    id: int
    kindle_path: str = KINDLE_DOCUMENTS_FOLDER

class UpdateBookRequest(BaseModel):
    title: str
    author: str
    series: Optional[str] = None
    volume: Optional[float] = None
    synopsis: Optional[str] = None
    publisher: Optional[str] = None
    publish_year: Optional[int] = None

class DeleteBookRequest(BaseModel):
    ids: List[int]
    permanent: bool = False

class DownloadCoverRequest(BaseModel):
    url: str

class SettingsRequest(BaseModel):
    books_folder: str
    scanner_threads: int = 2

class ProfileModel(BaseModel):
    id: int
    name: str
    avatar: Optional[str] = None

class ProfileCreateRequest(BaseModel):
    name: str
    avatar: Optional[str] = None

class ReadingProgressModel(BaseModel):
    id: int
    profile_id: int
    book_id: int
    cfi_location: str
    last_read: str

class ReadingProgressRequest(BaseModel):
    cfi_location: str

# === EVENT NOTIFIER FOR SSE ===
clients = set()
main_loop = None

def notify_clients(message: str):
    if main_loop:
        for q in list(clients):
            main_loop.call_soon_threadsafe(q.put_nowait, message)

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
        valid_extensions = ('.epub', '.mobi', '.azw3', '.azw', '.kfx', '.pdf', '.cbz', '.cbr', '.djvu')
        if ext in valid_extensions:
            file_name = os.path.basename(file_path)
            threading.Thread(target=self._process_delayed, args=(file_path, file_name, ext), daemon=True).start()

    def _process_delayed(self, file_path, file_name, ext):
        # Wait a bit while the file copies entirely
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
                return # File deleted
            time.sleep(1)
            retries += 1
            if retries > 60: # Limit retries to 60s
                break
                
        time.sleep(1)
        
        try:
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM books WHERE file_path = ?", (file_path,))
                if cursor.fetchone():
                    return
        except Exception:
            pass
                
        print(f"[Watchdog] Processando novo e-book detectado: {file_name}", flush=True)
        try:
            process_book(file_path, file_name, ext)
            notify_clients("new_book")
        except Exception as e:
            print(f"[Watchdog] Erro processando {file_name}: {e}", flush=True)

def start_watchdog():
    global global_observer
    books_folder = get_books_folder()
    if os.path.exists(books_folder):
        global_observer = Observer()
        global_observer.schedule(BookWatchdogHandler(), books_folder, recursive=True)
        global_observer.start()
        print(f"[Watchdog] Monitorando pasta: {books_folder}", flush=True)

def restart_watchdog():
    global global_observer
    if global_observer:
        try:
            global_observer.stop()
            global_observer.join()
        except Exception:
            pass
    start_watchdog()

def init_db():
    """Cria a tabela no SQLite se não existir."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Habilita o modo WAL para permitir leitura e escrita simultâneas no banco
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                file_type TEXT NOT NULL,
                cover_path TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            cursor.execute("ALTER TABLE books ADD COLUMN cover_path TEXT")
        except sqlite3.OperationalError:
            pass # A coluna já existe
        try:
            cursor.execute("ALTER TABLE books ADD COLUMN added_date TIMESTAMP")
            cursor.execute("UPDATE books SET added_date = CURRENT_TIMESTAMP WHERE added_date IS NULL")
        except sqlite3.OperationalError:
            pass # A coluna já existe
            
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                avatar TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                cfi_location TEXT NOT NULL,
                last_read TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id),
                FOREIGN KEY (book_id) REFERENCES books(id),
                UNIQUE(profile_id, book_id)
            )
        ''')
        
        # Insert Default Profile if not exists
        cursor.execute("INSERT OR IGNORE INTO profiles (id, name, avatar) VALUES (1, 'Visitante', NULL)")

        # Novas colunas de Metadados Avançados
        for col, col_type in [("series", "TEXT"), ("volume", "REAL"), ("synopsis", "TEXT"), ("publisher", "TEXT"), ("publish_year", "INTEGER")]:
            try:
                cursor.execute(f"ALTER TABLE books ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
                
        conn.commit()

def process_book(file_path, file, ext):
    """Processa um único livro: extrai metadados, capa e salva no DB."""
    # Extrai Metadados
    title = file
    author = "Desconhecido"
    cover_path = None
    try:
        if ext == '.pdf':
            # Tratamento especial usando PyMuPDF
            with fitz.open(file_path) as doc:
                pdf_meta = doc.metadata
                if pdf_meta and pdf_meta.get('title'):
                    title = pdf_meta['title']
                else:
                    title = os.path.splitext(file)[0]
                    
                if pdf_meta and pdf_meta.get('author'):
                    author = pdf_meta['author']
                    
                # Remove padrões como (Serie #1) do inicio do titulo
                title = re.sub(r'^\(.*?\)\s*', '', title)
                
                # Tenta extrair a capa (primeira página para PDF)
                try:
                    # Para PDF limita se for maior que 50MB
                    if len(doc) > 0 and os.path.getsize(file_path) < 50 * 1024 * 1024:
                        page = doc.load_page(0)
                        
                        # Define zoom inteligente (max 300px de largura) em vez de um fator numérico fixo
                        zoom = 300.0 / page.rect.width
                        if zoom > 1.0: zoom = 1.0 # Não amplia, apenas reduz
                        
                        mat = fitz.Matrix(zoom, zoom)
                        # Renderiza em baixa resolução e sem canal Alpha (economiza ~25% de memória)
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        cover_bytes = pix.tobytes("jpeg", 80) # Salva com 80% de qualidade
                        
                        # Liberação explícita da memória C do PyMuPDF
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
            # Extração via desempacotamento mobi e leitura do XML OPF
            temp_dir, extracted_filepath = mobi.extract(file_path)
            
            # Vasculha as entranhas atrás do OPF e da Capa
            for root_dir, local_dirs, local_files in os.walk(temp_dir):
                for f_name in local_files:
                    
                    # CAÇANDO O TÍTULO E AUTOR NO ARQUIVO OPF
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
                    
                    # CAÇANDO A CAPA
                    elif f_name.lower().endswith(('.jpg', '.jpeg', '.png')) and 'cover' in f_name.lower():
                        caminho_capa_temp = os.path.join(root_dir, f_name)
                        if not cover_path:
                            cover_filename = hashlib.md5(file_path.encode('utf-8')).hexdigest() + ".jpg"
                            cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                            shutil.copy(caminho_capa_temp, cover_full_path)
                            cover_path = f"/covers/{cover_filename}"
            
            # Limpa a sujeira
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        else:
            # Tratamento padrão para EPUB via ebookmeta
            meta = ebookmeta.get_metadata(file_path)
            title = meta.title if meta.title else os.path.splitext(file)[0]
            
            # Remove padrões como (Serie #1) do inicio do titulo
            title = re.sub(r'^\(.*?\)\s*', '', title)
            
            author = ", ".join(meta.author_list) if meta.author_list else "Desconhecido"
            
            if meta.cover_image_data:
                cover_filename = hashlib.md5(file_path.encode('utf-8')).hexdigest() + ".jpg"
                cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                with open(cover_full_path, "wb") as f:
                    f.write(meta.cover_image_data)
                cover_path = f"/covers/{cover_filename}"
            
    except Exception as e:
        # Em caso de erro, usa os valores padrão (nome do arquivo)
        pass
    
    # Renomeia fisicamente o arquivo antes de salvar no DB
    dir_name = os.path.dirname(file_path)
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
    safe_author = re.sub(r'[<>:"/\\|?*]', '', author)
    new_filename = f"{safe_author} - {safe_title}{ext}"
    new_path = os.path.join(dir_name, new_filename)
    
    # Protege para não renomear se o destino já existir para evitar conflitos
    if new_path != file_path and not os.path.exists(new_path):
        try:
            os.rename(file_path, new_path)
            file_path = new_path
        except Exception:
            pass
            
    # Salva no banco de dados
    # Como SQLite concorre mal em multi-thread, abrimos uma conexão por thread rápida
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
        # Formatos Kindle Padrão
        '.epub', '.mobi', '.azw3', '.azw', '.kfx', 
        # Formatos Suportados pelo KOReader
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
                    
                    # Verifica se o arquivo já está no Banco de Dados pelo caminho absoluto
                    cursor.execute("SELECT id FROM books WHERE file_path = ?", (file_path,))
                    if cursor.fetchone():
                        continue

                    
                    files_to_process.append((file_path, file, ext))

    if files_to_process:
        threads_count = get_scanner_threads()
        print(f"[Scanner] Processando {len(files_to_process)} novos arquivos usando {threads_count} threads...", flush=True)
        
        import queue
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
            
        q.join() # Aguarda processamento concluir
        
        # Envia sinal de encerramento para ass threads
        for _ in range(threads_count):
            q.put(None)

# Inicializa o DB e faz o scanner toda vez que a API inicia
# Inicializa o DB e faz o scanner toda vez que a API inicia
@app.on_event("startup")
def startup():
    global main_loop
    try:
        main_loop = asyncio.get_running_loop()
    except Exception:
        pass
    init_db()
    
    # Roda o scan_books em uma thread separada para não travar o Uvicorn durante a inicialização
    def run_scanner():
        print("[Scanner] Iniciando varredura da biblioteca em segundo plano...", flush=True)
        scan_books()
        print("[Scanner] Varredura concluída!", flush=True)
        
    threading.Thread(target=run_scanner, daemon=True).start()
    start_watchdog()

@app.on_event("shutdown")
def shutdown():
    global global_observer
    if global_observer:
        try:
            global_observer.stop()
            global_observer.join(timeout=2.0)
        except Exception:
            pass
    print("[Watchdog] Observer encerrado.", flush=True)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Renderiza a interface do frontend."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/events")
async def sse_events(request: Request):
    """Server-Sent Events endpoint for real-time frontend updates."""
    queue = asyncio.Queue()
    clients.add(queue)
    
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                # Use asyncio.wait_for to periodically check for disconnects
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=2.0)
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    pass
        except asyncio.CancelledError:
            pass
        finally:
            clients.remove(queue)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive"})

@app.get("/api/books", response_model=List[BookModel])
def get_books():
    """Retorna todos os livros cadastrados no SQLite."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books ORDER BY added_date DESC, title ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@app.put("/api/books/{book_id}")
def update_book(book_id: int, req: UpdateBookRequest):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Busca detalhes do arquivo atual para renomear
        cursor.execute("SELECT file_path, file_type FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Livro não encontrado no banco de dados.")
            
        old_path, ext = row
        new_path = old_path

        # Tenta renomear o arquivo localmente, se ele existir
        if os.path.exists(old_path):
            dir_name = os.path.dirname(old_path)
            
            # Limpa caracteres inválidos no Windows para nome de arquivo
            safe_title = re.sub(r'[<>:"/\\|?*]', '', req.title)
            safe_author = re.sub(r'[<>:"/\\|?*]', '', req.author)
            new_filename = f"{safe_author} - {safe_title}{ext}"
            new_path = os.path.join(dir_name, new_filename)
            
            if new_path != old_path:
                try:
                    os.rename(old_path, new_path)
                except Exception as e:
                    # Se falhar ao renomear o arquivo no Windows, não atualiza o caminho
                    new_path = old_path

        cursor.execute('''
            UPDATE books 
            SET title = ?, author = ?, file_path = ?, series = ?, volume = ?, synopsis = ?, publisher = ?, publish_year = ?
            WHERE id = ?
        ''', (req.title, req.author, new_path, req.series, req.volume, req.synopsis, req.publisher, req.publish_year, book_id))
        conn.commit()
        
    return {"status": "success", "message": "Livro atualizado e renomeado!"}

@app.post("/api/delete")
def delete_books(req: DeleteBookRequest):
    """Exclui livros do banco de dados e move/apaga os arquivos."""
    if not req.ids:
        return {"status": "success", "message": "Nenhum livro selecionado."}
        
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        placeholders = ','.join('?' for _ in req.ids)
        cursor.execute(f"SELECT id, file_path, cover_path FROM books WHERE id IN ({placeholders})", req.ids)
        rows = cursor.fetchall()
        
        for row in rows:
            book_id, file_path, cover_path = row
            try:
                if os.path.exists(file_path):
                    if req.permanent:
                        os.remove(file_path)
                    else:
                        file_name = os.path.basename(file_path)
                        # Trata nomes duplicados na lixeira
                        base_name, ext = os.path.splitext(file_name)
                        dest_path = os.path.join(TRASH_FOLDER, file_name)
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(TRASH_FOLDER, f"{base_name}_{counter}{ext}")
                            counter += 1
                        shutil.move(file_path, dest_path)
                
                # Excluir também a capa pra limpar espaço
                if cover_path:
                    # cover_path é tipo /covers/file.jpg, vamos pegar o basename
                    cover_filename = os.path.basename(cover_path)
                    cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                    if os.path.exists(cover_full_path):
                        os.remove(cover_full_path)
                        
            except Exception as e:
                # print(f"Erro ao excluir arquivo: {e}")
                pass
                
        cursor.execute(f"DELETE FROM books WHERE id IN ({placeholders})", req.ids)
        conn.commit()
        
    return {"status": "success", "message": f"{len(rows)} livro(s) excluído(s)."}

@app.get("/api/metadata/search")
def search_metadata(q: str):
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q={q}&langRestrict=pt"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 CalibreJr/1.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        
        results = []
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("items", []):
                vol = item.get("volumeInfo", {})
                
                title = vol.get("title", "")
                authors = ", ".join(vol.get("authors", []))
                synopsis = vol.get("description", "")
                publisher = vol.get("publisher", "")
                publish_date = vol.get("publishedDate", "")
                
                publish_year = None
                if publish_date:
                    try:
                        publish_year = int(publish_date.split("-")[0])
                    except Exception:
                        pass
                        
                cover_url = ""
                images = vol.get("imageLinks", {})
                if images:
                    cover_url = images.get("thumbnail", images.get("smallThumbnail", ""))
                    if cover_url:
                        cover_url = cover_url.replace("http://", "https://")
                        cover_url = cover_url.replace("zoom=1", "zoom=3").replace("&edge=curl", "")
                    
                results.append({
                    "title": title,
                    "author": authors,
                    "synopsis": synopsis,
                    "publisher": publisher,
                    "publish_year": publish_year,
                    "cover_url": cover_url
                })

        # Fallback to OpenLibrary if Google Books failed or returned nothing
        if len(results) == 0:
            ol_url = f"https://openlibrary.org/search.json?q={q}&limit=5"
            ol_resp = requests.get(ol_url, headers=headers, timeout=10)
            if ol_resp.status_code == 200:
                ol_data = ol_resp.json()
                for doc in ol_data.get("docs", []):
                    title = doc.get("title", "")
                    authors = ", ".join(doc.get("author_name", []))
                    publish_year = doc.get("first_publish_year", None)
                    publisher = ", ".join(doc.get("publisher", []))[:100] if doc.get("publisher") else ""
                    
                    cover_url = ""
                    if doc.get("cover_i"):
                        cover_url = f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-L.jpg"
                        
                    results.append({
                        "title": title,
                        "author": authors,
                        "synopsis": "Descrição não disponível no OpenLibrary.",
                        "publisher": publisher,
                        "publish_year": publish_year,
                        "cover_url": cover_url
                    })

        if len(results) == 0:
            return {"status": "error", "message": "Nenhum resultado retornado pelas APIs (Google e OpenLibrary limitaram a busca ou nenhum dado existe)."}
            
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/books/{book_id}/download-cover")
def download_cover(book_id: int, req: DownloadCoverRequest):
    """Faz download de uma imagem da internet e define como capa do livro no BD."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM books WHERE id = ?", (book_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Livro não encontrado.")
            
            file_path = row[0]
            
            resp = requests.get(req.url, stream=True, timeout=10)
            resp.raise_for_status()
            
            cover_filename = hashlib.md5((file_path + req.url).encode('utf-8')).hexdigest() + ".jpg"
            cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
            
            with open(cover_full_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            cover_path_db = f"/covers/{cover_filename}"
            
            cursor.execute("UPDATE books SET cover_path = ? WHERE id = ?", (cover_path_db, book_id))
            conn.commit()
            
        return {"status": "success", "cover_path": cover_path_db}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/detect-device")
def detect_device():
    import string
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            docs_path = os.path.join(drive, "documents")
            system_path = os.path.join(drive, "system")
            
            # Check for KOReader installation
            koreader_dirs = ["koreader", "extensions/koreader", ".adds/koreader"]
            koreader_root = None
            for kd in koreader_dirs:
                full_kd = os.path.join(drive, kd)
                if os.path.exists(full_kd):
                    koreader_root = full_kd
                    break

            # Aceita se for um Kindle Clássico OU se apenas tiver a pasta KOReader (útil pra Pendrives simulados ou Kobo)
            is_kindle = os.path.exists(docs_path) and os.path.exists(system_path)
            
            if is_kindle or koreader_root:
                device_info = {
                    "connected": True,
                    "drive": drive.replace('\\', '/'),
                    "kindle_path": docs_path.replace('\\', '/') if os.path.exists(docs_path) else drive.replace('\\', '/'),
                    "has_koreader": bool(koreader_root),
                    "koreader_path": ""
                }
                
                if device_info["has_koreader"]:
                    # 1. Tentar ler o settings.reader.lua para descobrir a pasta exata!
                    settings_file = os.path.join(koreader_root, "settings.reader.lua")
                    found_path = None
                    if os.path.exists(settings_file):
                        try:
                            with open(settings_file, "r", encoding="utf-8") as f:
                                content = f.read()
                                # Busca por ["home_dir"] = "/mnt/us/Books"
                                match = re.search(r'\["home_dir"\]\s*=\s*"([^"]+)"', content)
                                if match:
                                    # O Kindle linux vê /mnt/us/Books. O Windows vê E:/Books
                                    linux_path = match.group(1)
                                    # Remove o "/mnt/us/" que é o root do kindle
                                    if linux_path.startswith("/mnt/us/"):
                                        relative_path = linux_path[8:]
                                    elif linux_path.startswith("/mnt/ext1/"): # PocketBook
                                        relative_path = linux_path[10:]
                                    else:
                                        # Fallback se tiver outra raiz louca, limpa barras iniciais
                                        relative_path = linux_path.lstrip('/')
                                        
                                    relative_path = relative_path.replace('/', '\\')
                                    found_path = os.path.join(drive, relative_path)
                                    if os.path.exists(found_path):
                                        device_info["koreader_path"] = found_path.replace('\\', '/')
                        except Exception:
                            pass
                    
                    # 2. Se falhar ou não achar, tenta as pastas comuns (Fallback)
                    if not device_info["koreader_path"]:
                        common_libs = ["library", "books", "livros", "downloads", "koreader/library"]
                        for cl in common_libs:
                            full_cl = os.path.join(drive, cl)
                            if os.path.exists(full_cl):
                                device_info["koreader_path"] = full_cl.replace('\\', '/')
                                break
                    
                    # 3. Se nada der certo, retorna a raiz do pendrive
                    if not device_info["koreader_path"]:
                        device_info["koreader_path"] = drive.replace('\\', '/')
                        
                return device_info
    
    return {"connected": False}

@app.get("/api/pick-folder")
def pick_folder():
    import tkinter as tk
    from tkinter import filedialog
    
    # Criar janela root do tkinter e esconder ela (só queremos a popup)
    root = tk.Tk()
    root.withdraw()
    # Forçar a janela a aparecer no topo
    root.attributes('-topmost', True)
    
    folder_path = filedialog.askdirectory(parent=root, title="Selecione a pasta de destino do KOReader")
    
    # Destruir a root ao terminar
    root.destroy()
    
    if folder_path:
        return {"status": "success", "path": folder_path.replace('\\', '/')}
    else:
        raise HTTPException(status_code=400, detail="Nenhuma pasta selecionada.")

@app.post("/api/send")
def send_to_kindle(req: SendBookRequest):
    """Copia o arquivo do livro listado no banco para o dispositivo Kindle. Suporta envio progressivo."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM books WHERE id = ?", (req.id,))
        row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Livro não encontrado no banco de dados.")
        
    file_path = row[0]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="O arquivo do livro não foi encontrado no seu computador.")
        
    if not os.path.exists(req.kindle_path):
        raise HTTPException(status_code=400, detail=f"Kindle não encontrado em '{req.kindle_path}'. Verifique a conexão USB e a letra do drive.")
        
    from fastapi.responses import StreamingResponse
    import json

    def generate():
        try:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(req.kindle_path, file_name)
            
            total_size = os.path.getsize(file_path)
            if total_size == 0:
                shutil.copy2(file_path, dest_path)
                yield json.dumps({"status": "success", "progress": 100}) + "\n"
                return

            chunk_size = 512 * 1024 # 512KB chunks
            copied = 0
            
            with open(file_path, "rb") as fsrc, open(dest_path, "wb") as fdst:
                while True:
                    chunk = fsrc.read(chunk_size)
                    if not chunk:
                        break
                    fdst.write(chunk)
                    copied += len(chunk)
                    progress = min(100, int((copied / total_size) * 100))
                    yield json.dumps({"status": "progress", "progress": progress}) + "\n"
            
            # Copia permissões/metadata
            shutil.copystat(file_path, dest_path)
            yield json.dumps({"status": "success", "progress": 100}) + "\n"
            
        except Exception as e:
            yield json.dumps({"status": "error", "detail": f"Erro ao copiar: {str(e)}"}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")

@app.get("/api/settings")
def get_settings():
    return {
        "books_folder": get_books_folder(),
        "scanner_threads": get_scanner_threads()
    }

@app.put("/api/settings")
def save_settings(req: SettingsRequest):
    if not os.path.exists(req.books_folder) or not os.path.isdir(req.books_folder):
        raise HTTPException(status_code=400, detail="A pasta informada não existe ou é inválida.")
    
    settings = {}
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except:
            pass
            
    settings["books_folder"] = req.books_folder
    settings["scanner_threads"] = req.scanner_threads
    
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)
        
    # Rescan em background para refletir a nova biblioteca/threads
    threading.Thread(target=scan_books, daemon=True).start()
    restart_watchdog()
    return {"status": "success", "message": "Configurações atualizadas."}

class StartScanRequest(BaseModel):
    folder_path: Optional[str] = None

@app.post("/api/start-scan")
def start_scan(req: StartScanRequest):
    """Aciona a rotina manualmente."""
    # Roda em thread pra não bloquear a resposta Web
    threading.Thread(target=scan_books, args=(req.folder_path,), daemon=True).start()
    return {"status": "success", "message": "Varredura iniciada em segundo plano."}

@app.get("/api/profiles", response_model=List[ProfileModel])
def get_profiles():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM profiles ORDER BY id ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@app.post("/api/profiles", response_model=ProfileModel)
def create_profile(req: ProfileCreateRequest):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO profiles (name, avatar) VALUES (?, ?)", (req.name, req.avatar))
            conn.commit()
            profile_id = cursor.lastrowid
            return {"id": profile_id, "name": req.name, "avatar": req.avatar}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Perfil com esse nome já existe.")

@app.get("/api/profiles/{profile_id}/progress", response_model=List[ReadingProgressModel])
def get_reading_progress(profile_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reading_progress WHERE profile_id = ?", (profile_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@app.get("/api/books/{book_id}/progress")
def get_book_progress(book_id: int, profile_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cfi_location FROM reading_progress WHERE book_id = ? AND profile_id = ?", (book_id, profile_id))
        row = cursor.fetchone()
        if row:
            return {"cfi_location": row[0]}
        return {"cfi_location": None}

@app.post("/api/books/{book_id}/progress")
def save_book_progress(book_id: int, profile_id: int, req: ReadingProgressRequest):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reading_progress (profile_id, book_id, cfi_location, last_read)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_id, book_id) DO UPDATE SET 
            cfi_location=excluded.cfi_location, 
            last_read=CURRENT_TIMESTAMP
        ''', (profile_id, book_id, req.cfi_location))
        conn.commit()
    return {"status": "success"}

@app.get("/api/books/{book_id}/file")
def get_book_file(book_id: int):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path, file_type FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Livro não encontrado.")
            
        file_path, file_type = row
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Arquivo físico do livro não encontrado.")
            
        if file_type.lower() != '.epub':
            raise HTTPException(status_code=400, detail="Apenas arquivos EPUB são suportados pelo leitor web no momento.")
            
        from fastapi.responses import FileResponse
        return FileResponse(file_path, media_type="application/epub+zip", filename=os.path.basename(file_path))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
