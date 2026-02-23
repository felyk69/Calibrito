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

class SendBookRequest(BaseModel):
    id: int
    kindle_path: str = KINDLE_DOCUMENTS_FOLDER

class UpdateBookRequest(BaseModel):
    title: str
    author: str

class DeleteBookRequest(BaseModel):
    ids: List[int]
    permanent: bool = False

class SettingsRequest(BaseModel):
    books_folder: str

def init_db():
    """Cria a tabela no SQLite se não existir."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                file_type TEXT NOT NULL,
                cover_path TEXT
            )
        ''')
        try:
            cursor.execute("ALTER TABLE books ADD COLUMN cover_path TEXT")
        except sqlite3.OperationalError:
            pass # A coluna já existe
        conn.commit()

def scan_books():
    """Varre a pasta local de ebooks e insere novos arquivos no SQLite."""
    books_folder = get_books_folder()
    
    if not os.path.exists(books_folder):
        os.makedirs(books_folder, exist_ok=True)
        return

    valid_extensions = (
        # Formatos Kindle Padrão
        '.epub', '.mobi', '.azw3', '.azw', '.kfx', 
        # Formatos Suportados pelo KOReader
        '.pdf', '.cbz', '.cbr', '.djvu'
    )
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        for root, dirs, files in os.walk(books_folder):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in valid_extensions:
                    file_path = os.path.join(root, file)
                    
                    # Verifica se o arquivo já está no Banco de Dados pelo caminho absoluto
                    cursor.execute("SELECT id, cover_path FROM books WHERE file_path = ?", (file_path,))
                    row = cursor.fetchone()
                    if row:
                        book_id, existing_cover = row
                        if not existing_cover:
                            try:
                                meta = ebookmeta.get_metadata(file_path)
                                if meta.cover_image_data:
                                    cover_filename = hashlib.md5(file_path.encode('utf-8')).hexdigest() + ".jpg"
                                    cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                                    with open(cover_full_path, "wb") as f:
                                        f.write(meta.cover_image_data)
                                    cursor.execute("UPDATE books SET cover_path = ? WHERE id = ?", (f"/covers/{cover_filename}", book_id))
                            except Exception:
                                pass
                        continue 
                    
                    # Extrai Metadados
                    title = file
                    author = "Desconhecido"
                    cover_path = None
                    try:
                        if ext == '.pdf':
                            # Tratamento especial para PDF usando PyMuPDF
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
                                
                                # Tenta extrair a capa (primeira página)
                                try:
                                    if len(doc) > 0:
                                        page = doc.load_page(0)
                                        # Renderiza em baixa resolução pra imagem de capa (reduz o tamanho)
                                        pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
                                        cover_bytes = pix.tobytes("jpeg")
                                        
                                        cover_filename = hashlib.md5(file_path.encode('utf-8')).hexdigest() + ".jpg"
                                        cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                                        with open(cover_full_path, "wb") as f:
                                            f.write(cover_bytes)
                                        cover_path = f"/covers/{cover_filename}"
                                except Exception:
                                    pass
                        else:
                            # Tratamento padrão para EPUB/MOBI/AZW3 via ebookmeta
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
                    
                    # Salva no banco de dados
                    cursor.execute('''
                        INSERT INTO books (title, author, file_path, file_type, cover_path)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (title, author, file_path, ext, cover_path))
        conn.commit()

# Inicializa o DB e faz o scanner toda vez que a API inicia
@app.on_event("startup")
def startup():
    init_db()
    scan_books()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Renderiza a interface do frontend."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/books", response_model=List[BookModel])
def get_books():
    """Retorna todos os livros cadastrados no SQLite."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books ORDER BY title ASC")
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
            SET title = ?, author = ?, file_path = ? 
            WHERE id = ?
        ''', (req.title, req.author, new_path, book_id))
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

@app.get("/api/detect-device")
def detect_device():
    import string
    for letter in string.ascii_uppercase:
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            docs_path = os.path.join(drive, "documents")
            system_path = os.path.join(drive, "system")
            # Kindle original geralmente tem as pastas documents e system
            if os.path.exists(docs_path) and os.path.exists(system_path):
                device_info = {
                    "connected": True,
                    "drive": drive.replace('\\', '/'),
                    "kindle_path": docs_path.replace('\\', '/'),
                    "has_koreader": False,
                    "koreader_path": ""
                }
                
                # Check for KOReader installation
                koreader_dirs = ["koreader", "extensions/koreader", ".adds/koreader"]
                koreader_root = None
                for kd in koreader_dirs:
                    full_kd = os.path.join(drive, kd)
                    if os.path.exists(full_kd):
                        device_info["has_koreader"] = True
                        koreader_root = full_kd
                        break
                
                if device_info["has_koreader"] and koreader_root:
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
    return {"books_folder": get_books_folder()}

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
    
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=4)
        
    # Rescan para refletir a nova biblioteca
    scan_books()
    return {"status": "success", "message": "Configurações atualizadas."}
