import os
import pytest
import sqlite3
import shutil
from fastapi.testclient import TestClient
from pathlib import Path

# Override environment variables for tests BEFORE importing app
os.environ["TESTING"] = "1"
os.environ["SETTINGS_FILE"] = "test_settings.json"
os.environ["DB_FILE"] = "test_library.db"
os.environ["BOOKS_FOLDER"] = "test_ebooks"
os.environ["KINDLE_DOCUMENTS_FOLDER"] = "test_kindle"
os.environ["COVERS_FOLDER"] = "test_covers"
os.environ["TRASH_FOLDER"] = "test_trash"

from app.main import app
from app.core.database import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Create and cleanup test directories and database."""
    folders = ["test_ebooks", "test_kindle", "test_covers", "test_trash"]
    
    # Create test folders
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        
    # Initialize test DB
    init_db()
    
    yield
    
    # Cleanup test folders and DB after all tests are done
    for folder in folders:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            
    if os.path.exists("test_library.db"):
        os.remove("test_library.db")
    if os.path.exists("test_library.db-shm"):
        os.remove("test_library.db-shm")
    if os.path.exists("test_library.db-wal"):
        os.remove("test_library.db-wal")
    if os.path.exists("test_settings.json"):
        os.remove("test_settings.json")


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh database session for a test and rolls back after."""
    conn = sqlite3.connect("test_library.db")
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    yield conn
    
    # Clean up books table after each test
    conn.execute("DELETE FROM books;")
    conn.commit()
    conn.close()


@pytest.fixture(scope="module")
def client():
    """Provides a FastAPI TestClient."""
    with TestClient(app) as client:
        yield client
