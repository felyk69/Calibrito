import sqlite3
from app.core.config import DB_FILE
from app.core.logger import get_logger

logger = get_logger("database")

def init_db():
    """Initialize SQLite database schema and run migrations."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Enable WAL mode for concurrent read/write access
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                file_path TEXT UNIQUE NOT NULL,
                file_type TEXT NOT NULL,
                cover_path TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        try:
            cursor.execute("ALTER TABLE books ADD COLUMN cover_path TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute("ALTER TABLE books ADD COLUMN added_date TIMESTAMP")
            cursor.execute("UPDATE books SET added_date = CURRENT_TIMESTAMP WHERE added_date IS NULL")
        except sqlite3.OperationalError:
            pass  # Column already exists
            
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                avatar TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reading_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                cfi_location TEXT NOT NULL,
                last_read TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (profile_id) REFERENCES profiles(id),
                FOREIGN KEY (book_id) REFERENCES books(id),
                UNIQUE(profile_id, book_id)
            )
        ''')
        
        # Insert Default Profile if not exists
        cursor.execute("INSERT OR IGNORE INTO profiles (id, name, avatar) VALUES (1, 'Guest', NULL)")

        # Advanced metadata columns (migration)
        _ALLOWED_COLS = {"series": "TEXT", "volume": "REAL", "synopsis": "TEXT", "publisher": "TEXT", "publish_year": "INTEGER"}
        for col, col_type in _ALLOWED_COLS.items():
            if col_type not in ("TEXT", "REAL", "INTEGER"):
                continue
            try:
                cursor.execute(
                    "ALTER TABLE books ADD COLUMN " + col + " " + col_type
                )
            except sqlite3.OperationalError:
                pass

        # Reading progress percentage column (for non-EPUB formats)
        try:
            cursor.execute("ALTER TABLE reading_progress ADD COLUMN progress_percent REAL")
        except sqlite3.OperationalError:
            pass
                
        conn.commit()
