import os
import json
from app.core.config import (
    get_kindle_folder,
    get_books_folder,
    get_scanner_threads,
    SETTINGS_FILE
)

def test_settings_default_values():
    """Test standard getters when no settings file exists initially."""
    if os.path.exists(SETTINGS_FILE):
        os.remove(SETTINGS_FILE)
        
    kindle_path = get_kindle_folder()
    assert isinstance(kindle_path, str)
    
    books_folder = get_books_folder()
    assert books_folder == os.getenv("BOOKS_FOLDER") # it was mocked in conftest
    
    threads = get_scanner_threads()
    assert threads == 2

def test_settings_saved_values():
    """Test standard getters read from JSON."""
    settings_data = {
        "kindle_folder": "Z:\\kindle_test",
        "books_folder": "Z:\\books_test",
        "scanner_threads": 4
    }
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings_data, f)
        
    # We must ensure to clear cache if config reads settings file
    assert get_kindle_folder() == "Z:\\kindle_test"
    # the folder checker checks if it is a dir, since Z:\books_test is not a dir, it falls back to DEFAULT.
    assert get_scanner_threads() == 4
