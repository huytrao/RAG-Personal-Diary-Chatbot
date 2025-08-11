import sqlite3
import os

DB_PATH = "./diary.db"

def test_database():
    """Test database operations"""
    try:
        # Remove existing database if it exists
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print("Removed existing database")
        
        # Create connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert test data
        cursor.execute(
            "INSERT INTO diary_entries (date, content) VALUES (?, ?)",
            ("2025-08-11", "Test entry content")
        )
        
        conn.commit()
        
        # Read back data
        cursor.execute("SELECT * FROM diary_entries")
        entries = cursor.fetchall()
        
        print(f"Database test successful! Found {len(entries)} entries:")
        for entry in entries:
            print(f"  ID: {entry[0]}, Date: {entry[1]}, Content: {entry[2][:50]}...")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Database test failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_database()