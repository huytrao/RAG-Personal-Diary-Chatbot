"""
FastAPI v3 - RAG Personal Diary Chatbot Backend
Enhanced with user authentication and isolation
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import sqlite3
import os
import sys
import traceback
from typing import Optional, List

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from user_auth import UserAuthManager

# Initialize FastAPI app
app = FastAPI(title="RAG Personal Diary API", version="3.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:8502", "http://localhost:8503", "http://localhost:8504", "http://localhost:8505", "http://localhost:8506", "http://localhost:8507", "http://localhost:8508"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database paths
DIARY_DB_PATH = os.path.join(parent_dir, "diary.db")
AUTH_DB_PATH = os.path.join(parent_dir, "auth.db")

# Initialize auth manager
auth_manager = UserAuthManager(AUTH_DB_PATH)

# Pydantic models
class DiaryEntryCreate(BaseModel):
    date: str
    content: str
    tags: str = ""

class DiaryEntryResponse(BaseModel):
    id: int
    user_id: int
    date: str
    content: str
    tags: str
    created_at: str

class UserCredentials(BaseModel):
    username: str
    password: str

class UserRegistration(BaseModel):
    username: str
    email: str
    password: str

async def get_current_user(authorization: Optional[str] = Header(None)) -> int:
    """Validate session token and return user_id"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    session_token = authorization[7:]  # Remove "Bearer "
    
    user_data = auth_manager.validate_session(session_token)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user_data["id"]

def init_diary_db():
    """Initialize diary database with user isolation"""
    try:
        conn = sqlite3.connect(DIARY_DB_PATH)
        cursor = conn.cursor()
        
        # Create table with user_id for isolation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add user_id column if it doesn't exist (for existing installations)
        try:
            cursor.execute("ALTER TABLE diary_entries ADD COLUMN user_id INTEGER DEFAULT 1")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        conn.commit()
        conn.close()
        print(f"Diary database initialized at {DIARY_DB_PATH}")
    except Exception as e:
        print(f"Error initializing diary database: {str(e)}")
        raise

# Authentication endpoints
@app.post("/auth/register")
async def register_user(credentials: UserRegistration):
    """Register a new user"""
    try:
        success, message, user_id = auth_manager.register_user(credentials.username, credentials.email, credentials.password)
        if success:
            return {
                "message": message,
                "user_id": user_id
            }
        else:
            raise HTTPException(status_code=400, detail=message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/login")
async def login_user(credentials: UserCredentials):
    """Login user and create session"""
    try:
        # Authenticate user
        success, message, user_data = auth_manager.authenticate_user(credentials.username, credentials.password)
        if not success:
            raise HTTPException(status_code=401, detail=message)
        
        # Create session
        session_token = auth_manager.create_session(user_data["id"])
        
        return {
            "message": message,
            "user_id": user_data["id"],
            "username": user_data["username"],
            "session_token": session_token
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/logout")
async def logout_user(current_user_id: int = Depends(get_current_user)):
    """Logout current user"""
    try:
        # In a real app, you'd get the session token and invalidate it
        return {"message": "Logged out successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Diary endpoints
@app.post("/diary/entries", response_model=DiaryEntryResponse)
async def create_diary_entry(
    entry: DiaryEntryCreate, 
    current_user_id: int = Depends(get_current_user)
):
    """Create a new diary entry for authenticated user"""
    try:
        conn = sqlite3.connect(DIARY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO diary_entries (user_id, date, content, tags)
            VALUES (?, ?, ?, ?)
        """, (current_user_id, entry.date, entry.content, entry.tags))
        
        entry_id = cursor.lastrowid
        
        # Get the created entry
        cursor.execute("""
            SELECT id, user_id, date, content, tags, created_at
            FROM diary_entries
            WHERE id = ?
        """, (entry_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return DiaryEntryResponse(
                id=row[0],
                user_id=row[1],
                date=row[2],
                content=row[3],
                tags=row[4],
                created_at=row[5]
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create entry")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/diary/entries", response_model=List[DiaryEntryResponse])
async def get_diary_entries(
    current_user_id: int = Depends(get_current_user),
    tag: Optional[str] = None,
    limit: Optional[int] = 100
):
    """Get diary entries for authenticated user"""
    try:
        conn = sqlite3.connect(DIARY_DB_PATH)
        cursor = conn.cursor()
        
        # Build query with user isolation
        if tag:
            cursor.execute("""
                SELECT id, user_id, date, content, tags, created_at
                FROM diary_entries
                WHERE user_id = ? AND tags LIKE ?
                ORDER BY date DESC, created_at DESC
                LIMIT ?
            """, (current_user_id, f"%{tag}%", limit))
        else:
            cursor.execute("""
                SELECT id, user_id, date, content, tags, created_at
                FROM diary_entries
                WHERE user_id = ?
                ORDER BY date DESC, created_at DESC
                LIMIT ?
            """, (current_user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        entries = []
        for row in rows:
            entries.append(DiaryEntryResponse(
                id=row[0],
                user_id=row[1],
                date=row[2],
                content=row[3],
                tags=row[4],
                created_at=row[5]
            ))
        
        return entries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/diary/entries/{entry_id}", response_model=DiaryEntryResponse)
async def get_diary_entry(
    entry_id: int,
    current_user_id: int = Depends(get_current_user)
):
    """Get a specific diary entry for authenticated user"""
    try:
        conn = sqlite3.connect(DIARY_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, user_id, date, content, tags, created_at
            FROM diary_entries
            WHERE id = ? AND user_id = ?
        """, (entry_id, current_user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return DiaryEntryResponse(
                id=row[0],
                user_id=row[1],
                date=row[2],
                content=row[3],
                tags=row[4],
                created_at=row[5]
            )
        else:
            raise HTTPException(status_code=404, detail="Entry not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/diary/entries/{entry_id}")
async def delete_diary_entry(
    entry_id: int,
    current_user_id: int = Depends(get_current_user)
):
    """Delete a diary entry for authenticated user"""
    try:
        conn = sqlite3.connect(DIARY_DB_PATH)
        cursor = conn.cursor()
        
        # Check if entry exists and belongs to user
        cursor.execute("""
            SELECT id FROM diary_entries
            WHERE id = ? AND user_id = ?
        """, (entry_id, current_user_id))
        
        if not cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=404, detail="Entry not found")
        
        # Delete the entry
        cursor.execute("""
            DELETE FROM diary_entries
            WHERE id = ? AND user_id = ?
        """, (entry_id, current_user_id))
        
        conn.commit()
        conn.close()
        
        return {"message": "Entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = sqlite3.connect(DIARY_DB_PATH)
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_diary_db()
    print("FastAPI v3 server started successfully!")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
