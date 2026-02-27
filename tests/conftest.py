import os
import pytest
from fastapi.testclient import TestClient

# Set testing environment variables before importing app
os.environ["TESTING"] = "1"

@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    # Create a temporary directory for DB
    db_dir = tmp_path_factory.mktemp("db")
    db_file = db_dir / "test_library.db"
    return str(db_file)

@pytest.fixture(scope="session", autouse=True)
def setup_test_env(test_db_path, tmp_path_factory):
    import app.core.config as config
    config.DB_FILE = test_db_path
    
    # Fake directories
    covers_dir = tmp_path_factory.mktemp("covers")
    books_dir = tmp_path_factory.mktemp("ebooks")
    trash_dir = tmp_path_factory.mktemp("trash")
    
    config.COVERS_FOLDER = str(covers_dir)
    config.TRASH_FOLDER = str(trash_dir)
    config.DEFAULT_BOOKS_FOLDER = str(books_dir)
    config.get_books_folder = lambda: str(books_dir)

    # Initialize the database
    from app.core.database import init_db
    init_db()

@pytest.fixture
def client():
    from app.main import app
    with TestClient(app) as client:
        yield client
