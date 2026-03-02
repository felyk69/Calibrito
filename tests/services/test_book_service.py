import os
import sqlite3
import pytest
from app.services.book_service import process_book
from app.core.database import get_db_connection

def test_process_book_unsupported_file(db_session):
    """Ensure process_book handles generic/unsupported files without crashing and saves to DB."""
    dummy_file = "test_ebooks/dummy.txt"
    with open(dummy_file, "w") as f:
        f.write("test content")
        
    process_book(dummy_file, "dummy.txt", ".txt")
    
    # Check DB
    cursor = db_session.cursor()
    cursor.execute("SELECT title, author, file_type FROM books WHERE file_path = ?", (dummy_file,))
    row = cursor.fetchone()
    
    assert row is not None
    assert row[1] == "Unknown"
    assert row[2] == ".txt"

def test_process_book_missing_file(db_session):
    """Ensure process_book handles missing files gracefully."""
    # missing file should not trigger a permission error if it doesn't exist
    missing_file = "test_ebooks/missing.epub"
    if os.path.exists(missing_file):
        os.remove(missing_file)
        
    process_book(missing_file, "missing.epub", ".epub")
    
    cursor = db_session.cursor()
    cursor.execute("SELECT title, author FROM books WHERE file_path = ?", (missing_file,))
    row = cursor.fetchone()
    
    assert row is not None
    # since file is missing, metadata extraction fails, title defaults to "missing.epub" or "missing", author "Unknown"
    assert "missing" in row[0].lower()
