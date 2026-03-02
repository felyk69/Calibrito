import hashlib
import json
import os
import re
import shutil
import sqlite3
import unicodedata
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from app.core.config import COVERS_FOLDER, TRASH_FOLDER, get_kindle_folder
from app.core.database import get_db
from app.core.logger import get_logger
from app.models.schemas import BookModel, DeleteBookRequest, SendBookRequest, UpdateBookRequest

logger = get_logger("routes.books")

router = APIRouter(prefix="/api/v1", tags=["Books"])


# ── Auto-Rename ──
@router.post("/books/auto-rename")
def auto_rename_books(db: sqlite3.Connection = Depends(get_db)):
    renamed = 0
    skipped = 0
    errors = []

    conn = db
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, author, file_path, file_type FROM books")
    rows = cursor.fetchall()

    for book_id, title, author, file_path, ext in rows:
        if not os.path.exists(file_path):
            errors.append({"id": book_id, "title": title, "reason": "Arquivo não encontrado"})
            continue

        safe_title = re.sub(r'[<>:"/\\|?*]', "", title).strip()
        safe_author = re.sub(r'[<>:"/\\|?*]', "", author).strip()
        new_filename = f"{safe_author} - {safe_title}{ext}"
        dir_name = os.path.dirname(file_path)
        new_path = os.path.join(dir_name, new_filename)

        if new_path == file_path:
            skipped += 1
            continue

        if os.path.exists(new_path) and new_path.lower() != file_path.lower():
            errors.append({"id": book_id, "title": title, "reason": f"Já existe: {new_filename}"})
            continue

        try:
            os.rename(file_path, new_path)
            cursor.execute("UPDATE books SET file_path = ? WHERE id = ?", (new_path, book_id))
            renamed += 1
        except Exception as e:
            errors.append({"id": book_id, "title": title, "reason": str(e)})

    conn.commit()

    return {"renamed": renamed, "skipped": skipped, "errors": errors}


# ── Duplicate Scanner ──
def _normalize(text):
    """Remove accents, punctuation, and normalize for comparison."""
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9\s]", "", text)
    return " ".join(text.split())


def _file_md5(path, chunk_size=8192):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(chunk_size):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


@router.get("/books/duplicates")
def find_duplicates(db: sqlite3.Connection = Depends(get_db)):
    FORMAT_PRIORITY = {".epub": 0, ".azw3": 1, ".mobi": 2, ".pdf": 3}

    conn = db
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books ORDER BY title ASC")
    all_books = [dict(row) for row in cursor.fetchall()]

    groups = []
    seen_ids = set()

    def sort_by_format(books):
        return sorted(books, key=lambda b: FORMAT_PRIORITY.get(b["file_type"].lower(), 99))

    # Pass 1: Hash duplicates (exact file copies)
    hash_map = defaultdict(list)
    for book in all_books:
        md5 = _file_md5(book["file_path"])
        if md5:
            hash_map[md5].append(book)

    for md5, books in hash_map.items():
        if len(books) > 1:
            for b in books:
                seen_ids.add(b["id"])
            groups.append({"reason": "hash", "detail": f"MD5: {md5[:12]}…", "books": sort_by_format(books)})

    # Pass 2: Metadata duplicates (same title + author, normalized)
    meta_map = defaultdict(list)
    for book in all_books:
        if book["id"] in seen_ids:
            continue
        key = _normalize(book["title"]) + "||" + _normalize(book["author"])
        meta_map[key].append(book)

    for _key, books in meta_map.items():
        if len(books) > 1:
            sorted_books = sort_by_format(books)
            groups.append(
                {
                    "reason": "metadata",
                    "detail": f"{sorted_books[0]['title']} — {sorted_books[0]['author']}",
                    "books": sorted_books,
                }
            )

    return {"groups": groups, "total_groups": len(groups)}


@router.get("/books", response_model=list[BookModel])
def get_books(db: sqlite3.Connection = Depends(get_db)):
    conn = db
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books ORDER BY added_date DESC, title ASC")
    rows = cursor.fetchall()
    return [dict(row) for row in rows]


@router.put("/books/{book_id}")
def update_book(book_id: int, req: UpdateBookRequest, db: sqlite3.Connection = Depends(get_db)):
    conn = db
    cursor = conn.cursor()
    cursor.execute("SELECT file_path, file_type FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Livro não encontrado no banco de dados.")

    old_path, ext = row
    new_path = old_path

    if os.path.exists(old_path):
        dir_name = os.path.dirname(old_path)
        safe_title = re.sub(r'[<\\>:"/\\\\|?*]', "", req.title)
        safe_author = re.sub(r'[<\\>:"/\\\\|?*]', "", req.author)
        new_filename = f"{safe_author} - {safe_title}{ext}"
        new_path = os.path.join(dir_name, new_filename)

        if new_path != old_path:
            try:
                os.rename(old_path, new_path)
            except OSError as e:
                logger.warning("Failed to rename book file %s: %s", old_path, e)
                new_path = old_path

    cursor.execute(
        """
        UPDATE books
        SET title = ?, author = ?, file_path = ?, series = ?, volume = ?, synopsis = ?, publisher = ?, publish_year = ?
        WHERE id = ?
    """,
        (
            req.title,
            req.author,
            new_path,
            req.series,
            req.volume,
            req.synopsis,
            req.publisher,
            req.publish_year,
            book_id,
        ),
    )
    conn.commit()

    return {"status": "success", "message": "Book updated and renamed!"}


@router.post("/delete")
def delete_books(req: DeleteBookRequest, db: sqlite3.Connection = Depends(get_db)):
    if not req.ids:
        return {"status": "success", "message": "No books selected."}

    conn = db
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in req.ids)
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

        except OSError as e:
            logger.warning("Failed to delete/move file for book %d: %s", book_id, e)

    cursor.execute(f"DELETE FROM books WHERE id IN ({placeholders})", req.ids)
    conn.commit()

    return {"status": "success", "message": f"{len(rows)} book(s) deleted."}


@router.post("/send")
def send_to_kindle(req: SendBookRequest, db: sqlite3.Connection = Depends(get_db)):
    kindle_path = req.kindle_path.strip() if req.kindle_path else ""
    if not kindle_path:
        kindle_path = get_kindle_folder()

    conn = db
    cursor = conn.cursor()
    cursor.execute("SELECT file_path FROM books WHERE id = ?", (req.id,))
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Livro não encontrado no banco de dados.")

    file_path = row[0]

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo original do livro não encontrado no disco.")

    if not os.path.exists(kindle_path):
        raise HTTPException(status_code=400, detail=f"Kindle not found at '{kindle_path}'.")

    def generate():
        try:
            file_name = os.path.basename(file_path)
            dest_path = os.path.join(kindle_path, file_name)

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
            yield json.dumps({"status": "error", "detail": f"Erro ao copiar arquivo: {str(e)}"}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


MIME_TYPES = {
    ".epub": "application/epub+zip",
    ".mobi": "application/x-mobipocket-ebook",
    ".azw3": "application/x-mobipocket-ebook",
    ".pdf": "application/pdf",
    ".fb2": "application/xml",
    ".cbz": "application/zip",
}


@router.get("/books/{book_id}/file")
def get_book_file(book_id: int, db: sqlite3.Connection = Depends(get_db)):
    conn = db
    cursor = conn.cursor()
    cursor.execute("SELECT file_path, file_type FROM books WHERE id = ?", (book_id,))
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Livro não encontrado.")

    file_path, file_type = row
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo original do livro não encontrado no disco.")

    ext = file_type.lower()
    media_type = MIME_TYPES.get(ext, "application/octet-stream")

    return FileResponse(file_path, media_type=media_type, filename=os.path.basename(file_path))
