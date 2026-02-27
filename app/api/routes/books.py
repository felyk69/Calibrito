import os
import shutil
import sqlite3
import re
from typing import List
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
import json

from app.core.config import DB_FILE, TRASH_FOLDER, COVERS_FOLDER, KINDLE_DOCUMENTS_FOLDER
from app.models.schemas import BookModel, UpdateBookRequest, DeleteBookRequest, SendBookRequest
from app.services.book_service import process_book

router = APIRouter(prefix="/api", tags=["Books"])

@router.get("/books", response_model=List[BookModel])
def get_books():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books ORDER BY added_date DESC, title ASC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

@router.put("/books/{book_id}")
def update_book(book_id: int, req: UpdateBookRequest):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path, file_type FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Livro não encontrado no banco de dados.")
            
        old_path, ext = row
        new_path = old_path

        if os.path.exists(old_path):
            dir_name = os.path.dirname(old_path)
            safe_title = re.sub(r'[<\\>:"/\\\\|?*]', '', req.title)
            safe_author = re.sub(r'[<\\>:"/\\\\|?*]', '', req.author)
            new_filename = f"{safe_author} - {safe_title}{ext}"
            new_path = os.path.join(dir_name, new_filename)
            
            if new_path != old_path:
                try:
                    os.rename(old_path, new_path)
                except Exception:
                    new_path = old_path

        cursor.execute('''
            UPDATE books 
            SET title = ?, author = ?, file_path = ?, series = ?, volume = ?, synopsis = ?, publisher = ?, publish_year = ?
            WHERE id = ?
        ''', (req.title, req.author, new_path, req.series, req.volume, req.synopsis, req.publisher, req.publish_year, book_id))
        conn.commit()
        
    return {"status": "success", "message": "Livro atualizado e renomeado!"}

@router.post("/delete")
def delete_books(req: DeleteBookRequest):
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
                        base_name, ext = os.path.splitext(file_name)
                        dest_path = os.path.join(TRASH_FOLDER, file_name)
                        counter = 1
                        while os.path.exists(dest_path):
                            dest_path = os.path.join(TRASH_FOLDER, f"{base_name}_{counter}{ext}")
                            counter += 1
                        shutil.move(file_path, dest_path)
                
                if cover_path:
                    cover_filename = os.path.basename(cover_path)
                    cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
                    if os.path.exists(cover_full_path):
                        os.remove(cover_full_path)
                        
            except Exception:
                pass
                
        cursor.execute(f"DELETE FROM books WHERE id IN ({placeholders})", req.ids)
        conn.commit()
        
    return {"status": "success", "message": f"{len(rows)} livro(s) excluído(s)."}

@router.post("/send")
def send_to_kindle(req: SendBookRequest):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_path FROM books WHERE id = ?", (req.id,))
        row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Livro não encontrado no banco de dados.")
        
    file_path = row[0]
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="O arquivo do livro não foi encontrado.")
        
    if not os.path.exists(req.kindle_path):
        raise HTTPException(status_code=400, detail=f"Kindle não encontrado em '{req.kindle_path}'.")

    def generate():
        try:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(req.kindle_path, file_name)
            
            total_size = os.path.getsize(file_path)
            if total_size == 0:
                shutil.copy2(file_path, dest_path)
                yield json.dumps({"status": "success", "progress": 100}) + "\n"
                return

            chunk_size = 512 * 1024
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
            
            shutil.copystat(file_path, dest_path)
            yield json.dumps({"status": "success", "progress": 100}) + "\n"
            
        except Exception as e:
            yield json.dumps({"status": "error", "detail": f"Erro ao copiar: {str(e)}"}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")

@router.get("/books/{book_id}/file")
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
            
        return FileResponse(file_path, media_type="application/epub+zip", filename=os.path.basename(file_path))
