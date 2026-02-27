import sqlite3
from app.core.config import DB_FILE

def init_db():
    """Cria a tabela no SQLite se não existir."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Habilita o modo WAL para permitir leitura e escrita simultâneas no banco
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
            pass # A coluna já existe
        try:
            cursor.execute("ALTER TABLE books ADD COLUMN added_date TIMESTAMP")
            cursor.execute("UPDATE books SET added_date = CURRENT_TIMESTAMP WHERE added_date IS NULL")
        except sqlite3.OperationalError:
            pass # A coluna já existe
            
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
        cursor.execute("INSERT OR IGNORE INTO profiles (id, name, avatar) VALUES (1, 'Visitante', NULL)")

        # Novas colunas de Metadados Avançados
        for col, col_type in [("series", "TEXT"), ("volume", "REAL"), ("synopsis", "TEXT"), ("publisher", "TEXT"), ("publish_year", "INTEGER")]:
            try:
                cursor.execute(f"ALTER TABLE books ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
                
        conn.commit()
