import sqlite3

def create_auth_database():
    """Create authentication database if not exists"""
    try:
        conn = sqlite3.connect("./user_db/auth.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Authentication database created successfully")
        
    except Exception as e:
        print(f"❌ Error creating auth database: {e}")

# Chạy function này
create_auth_database()