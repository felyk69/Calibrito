import sqlite3
import pytest
from app.core.database import get_db_connection, DB_FILE

def test_get_db_connection_context_manager():
    """Ensure the db connection yields and closes correctly."""
    with get_db_connection() as conn:
        assert isinstance(conn, sqlite3.Connection)
        
        # Test inserting and reading
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='books'")
        result = cursor.fetchone()
        assert result is not None, "Books table should exist."

def test_get_db_connection_rollback():
    """Ensure DB rolls back on exception."""
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO books (title, author, file_path, file_type) VALUES ('Err Title', 'Err Auth', '/err/path.epub', '.epub')")
            raise ValueError("Intentional error")
    except ValueError:
        pass
        
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE title='Err Title'")
        assert cursor.fetchone() is None, "Row should have been rolled back"
