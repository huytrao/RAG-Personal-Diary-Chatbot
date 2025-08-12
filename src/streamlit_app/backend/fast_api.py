from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import os
import traceback

app = FastAPI()

DB_PATH = "./diary.db"

class DiaryEntry(BaseModel):
    date: str
    content: str
    tags: str = ""  # Add tags field with default empty string

def init_db_if_not_exists():
    """Initialize database if it doesn't exist"""
    try:
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
        print(f"Database initialized successfully at {DB_PATH}")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise

@app.post("/submit_diary")
async def submit_diary_entry(entry: DiaryEntry):
    """Submit a new diary entry to the database"""
    try:
        print(f"Received entry: date={entry.date}, content_length={len(entry.content)}")
        
        # Initialize database
        init_db_if_not_exists()
        
        # Connect and insert
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print(f"Inserting into database: date='{entry.date}', content='{entry.content[:50]}...', tags='{entry.tags}'")
        
        cursor.execute(
            "INSERT INTO diary_entries (date, content, tags) VALUES (?, ?, ?)",
            (entry.date, entry.content, entry.tags)
        )
        
        conn.commit()
        entry_id = cursor.lastrowid
        conn.close()
        
        print(f"Entry saved successfully with ID: {entry_id}")
        
        return {
            "message": "Diary entry saved successfully",
            "entry_id": entry_id,
            "date": entry.date
        }
        
    except sqlite3.Error as e:
        error_msg = f"Database error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/")
async def root():
    return {"message": "Diary API is running"}

@app.get("/entries")
async def get_diary_entries():
    """Get all diary entries"""
    try:
        print("Fetching entries from database...")
        
        # Initialize database
        init_db_if_not_exists()
        
        # Check if database file exists
        if not os.path.exists(DB_PATH):
            print("Database file doesn't exist, returning empty entries")
            return {"entries": []}
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='diary_entries'
        """)
        if not cursor.fetchone():
            print("Table doesn't exist, returning empty entries")
            conn.close()
            return {"entries": []}
        
        cursor.execute("SELECT id, date, content, tags, created_at FROM diary_entries ORDER BY created_at DESC")
        entries = cursor.fetchall()
        conn.close()
        
        print(f"Found {len(entries)} entries")
        
        return {
            "entries": [
                {
                    "id": entry[0],
                    "date": entry[1], 
                    "content": entry[2],
                    "tags": entry[3] if len(entry) > 3 else "",  # Handle entries without tags
                    "created_at": entry[4] if len(entry) > 4 else entry[3]  # Handle old schema
                }
                for entry in entries
            ]
        }
        
    except sqlite3.Error as e:
        error_msg = f"Database error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

@app.delete("/entries/{entry_id}")
async def delete_diary_entry(entry_id: int):
    """Delete a diary entry by ID"""
    try:
        print(f"Attempting to delete entry with ID: {entry_id}")
        
        # Initialize database
        init_db_if_not_exists()
        
        # Check if database file exists
        if not os.path.exists(DB_PATH):
            print("Database file doesn't exist")
            raise HTTPException(status_code=404, detail="Database not found")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if entry exists
        cursor.execute("SELECT id FROM diary_entries WHERE id = ?", (entry_id,))
        if not cursor.fetchone():
            conn.close()
            print(f"Entry with ID {entry_id} not found")
            raise HTTPException(status_code=404, detail="Entry not found")
        
        # Delete the entry
        cursor.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            conn.close()
            print(f"No entry was deleted for ID {entry_id}")
            raise HTTPException(status_code=404, detail="Entry not found")
        
        conn.close()
        print(f"Entry {entry_id} deleted successfully")
        
        return {
            "message": "Diary entry deleted successfully",
            "deleted_id": entry_id
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except sqlite3.Error as e:
        error_msg = f"Database error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=error_msg)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    print("Starting up FastAPI application...")
    init_db_if_not_exists()
    print("Startup complete!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)