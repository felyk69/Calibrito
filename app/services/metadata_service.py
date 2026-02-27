import os
import re
import hashlib
import requests
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi import HTTPException
from app.core.config import DB_FILE, COVERS_FOLDER

def _is_isbn(q: str) -> bool:
    """Detect if query looks like an ISBN (10 or 13 digits)."""
    cleaned = re.sub(r'[\s\-]', '', q)
    return bool(re.match(r'^\d{10}(\d{3})?$', cleaned)) or bool(re.match(r'^\d{9}[0-9Xx]$', cleaned))

def _search_google_books(q: str, is_isbn: bool) -> list:
    """Search Google Books API."""
    try:
        if is_isbn:
            cleaned = re.sub(r'[\s\-]', '', q)
            query = f"isbn:{cleaned}"
        else:
            query = q
        
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=8"
        headers = {"User-Agent": "CalibreJr/2.0 (Book Manager)"}
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
                language = vol.get("language", "")
                categories = vol.get("categories", [])
                
                publish_year = None
                if publish_date:
                    try:
                        publish_year = int(publish_date.split("-")[0])
                    except Exception:
                        pass
                
                # Get best cover image
                cover_url = ""
                images = vol.get("imageLinks", {})
                if images:
                    cover_url = images.get("thumbnail", images.get("smallThumbnail", ""))
                    if cover_url:
                        cover_url = cover_url.replace("http://", "https://")
                        cover_url = cover_url.replace("zoom=1", "zoom=3").replace("&edge=curl", "")
                
                # Extract ISBN
                isbn = ""
                for ident in vol.get("industryIdentifiers", []):
                    if ident.get("type") == "ISBN_13":
                        isbn = ident.get("identifier", "")
                        break
                    elif ident.get("type") == "ISBN_10":
                        isbn = ident.get("identifier", "")
                
                results.append({
                    "title": title,
                    "author": authors,
                    "synopsis": synopsis,
                    "publisher": publisher,
                    "publish_year": publish_year,
                    "cover_url": cover_url,
                    "language": language,
                    "tags": categories,
                    "isbn": isbn,
                    "source": "Google Books"
                })
        return results
    except Exception:
        return []

def _search_openlibrary(q: str, is_isbn: bool) -> list:
    """Search OpenLibrary API."""
    try:
        headers = {"User-Agent": "CalibreJr/2.0 (calibrejr@app; Book Manager)"}
        
        if is_isbn:
            cleaned = re.sub(r'[\s\-]', '', q)
            # Use ISBN endpoint for direct lookup
            url = f"https://openlibrary.org/isbn/{cleaned}.json"
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                edition = resp.json()
                title = edition.get("title", "")
                publish_year = None
                pub_date = edition.get("publish_date", "")
                if pub_date:
                    match = re.search(r'\d{4}', pub_date)
                    if match:
                        publish_year = int(match.group())
                
                publishers = edition.get("publishers", [])
                publisher = publishers[0] if publishers else ""
                
                # Get authors
                authors = []
                for author_ref in edition.get("authors", []):
                    author_key = author_ref.get("key", "")
                    if author_key:
                        try:
                            a_resp = requests.get(f"https://openlibrary.org{author_key}.json", headers=headers, timeout=5)
                            if a_resp.status_code == 200:
                                authors.append(a_resp.json().get("name", ""))
                        except Exception:
                            pass
                
                # Cover
                cover_url = ""
                covers = edition.get("covers", [])
                if covers:
                    cover_url = f"https://covers.openlibrary.org/b/id/{covers[0]}-L.jpg"
                elif cleaned:
                    cover_url = f"https://covers.openlibrary.org/b/isbn/{cleaned}-L.jpg?default=false"
                
                # Description
                desc = edition.get("description", "")
                if isinstance(desc, dict):
                    desc = desc.get("value", "")
                
                return [{
                    "title": title,
                    "author": ", ".join(authors),
                    "synopsis": desc or "No description available.",
                    "publisher": publisher,
                    "publish_year": publish_year,
                    "cover_url": cover_url,
                    "language": "",
                    "tags": edition.get("subjects", [])[:5] if edition.get("subjects") else [],
                    "isbn": cleaned,
                    "source": "Open Library"
                }]
            return []
        else:
            # Title/general search
            url = f"https://openlibrary.org/search.json?q={q}&limit=5&fields=title,author_name,first_publish_year,publisher,cover_i,isbn,subject,key"
            resp = requests.get(url, headers=headers, timeout=10)
            results = []
            if resp.status_code == 200:
                data = resp.json()
                for doc in data.get("docs", []):
                    title = doc.get("title", "")
                    authors = ", ".join(doc.get("author_name", []))
                    publish_year = doc.get("first_publish_year", None)
                    publisher = ", ".join(doc.get("publisher", [])[:2]) if doc.get("publisher") else ""
                    
                    cover_url = ""
                    if doc.get("cover_i"):
                        cover_url = f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-L.jpg"
                    
                    isbns = doc.get("isbn", [])
                    isbn = isbns[0] if isbns else ""
                    
                    subjects = doc.get("subject", [])[:5] if doc.get("subject") else []
                    
                    results.append({
                        "title": title,
                        "author": authors,
                        "synopsis": "",
                        "publisher": publisher,
                        "publish_year": publish_year,
                        "cover_url": cover_url,
                        "language": "",
                        "tags": subjects,
                        "isbn": isbn,
                        "source": "Open Library"
                    })
            return results
    except Exception:
        return []


def search_metadata(q: str):
    """Search multiple sources in parallel and merge results."""
    try:
        is_isbn = _is_isbn(q)
        
        google_results = []
        openlibrary_results = []
        
        # Search both sources in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(_search_google_books, q, is_isbn): "google",
                executor.submit(_search_openlibrary, q, is_isbn): "openlibrary"
            }
            for future in as_completed(futures):
                source = futures[future]
                try:
                    result = future.result()
                    if source == "google":
                        google_results = result
                    else:
                        openlibrary_results = result
                except Exception:
                    pass
        
        # Merge: Google first, then OpenLibrary (avoiding exact title+author dupes)
        results = list(google_results)
        seen = {(r["title"].lower(), r["author"].lower()) for r in results}
        
        for r in openlibrary_results:
            key = (r["title"].lower(), r["author"].lower())
            if key not in seen:
                results.append(r)
                seen.add(key)
        
        if not results:
            return {"status": "error", "message": "Nenhum resultado encontrado no Google Books nem OpenLibrary."}
        
        return {"status": "success", "results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def download_cover(book_id: int, url: str):
    """Download an image from the internet and set as book cover in DB."""
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
