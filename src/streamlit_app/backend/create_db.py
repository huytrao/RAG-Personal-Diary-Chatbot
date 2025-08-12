# Database setup
import sqlite3
DB_PATH = "./diary.db"

def init_db():
    """Initialize the database with diary table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Add tags column to existing table if it doesn't exist
    try:
        cursor.execute("ALTER TABLE diary_entries ADD COLUMN tags TEXT DEFAULT ''")
        conn.commit()
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()