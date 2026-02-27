import os
import hashlib
import requests
import sqlite3
from fastapi import HTTPException
from app.core.config import DB_FILE, COVERS_FOLDER

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

        # Fallback to OpenLibrary
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

def download_cover(book_id: int, url: str):
    """Faz download de uma imagem da internet e define como capa do livro no BD."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM books WHERE id = ?", (book_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Livro não encontrado.")
            
            file_path = row[0]
            
            resp = requests.get(url, stream=True, timeout=10)
            resp.raise_for_status()
            
            cover_filename = hashlib.md5((file_path + url).encode('utf-8')).hexdigest() + ".jpg"
            cover_full_path = os.path.join(COVERS_FOLDER, cover_filename)
            
            with open(cover_full_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            cover_path_db = f"/covers/{cover_filename}"
            
            cursor.execute("UPDATE books SET cover_path = ? WHERE id = ?", (cover_path_db, book_id))
            conn.commit()
            
        return cover_path_db
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
