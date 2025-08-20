import requests
import streamlit as st
import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# API configuration
API_BASE_URL = "http://127.0.0.1:8004"

def get_auth_headers() -> Dict[str, str]:
    """Get authentication headers from session state"""
    session_token = getattr(st.session_state, 'session_token', None)
    if session_token:
        return {"Authorization": f"Bearer {session_token}"}
    return {}

def check_api_connection() -> bool:
    """Check if the API is running and accessible"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def submit_text_to_database_direct(entry: Dict[str, Any], user_id: int = 1) -> bool:
    """
    Submit diary entry directly to SQLite database (fallback when API is not available).
    
    Args:
        entry: Dictionary containing diary entry data
        user_id: ID of the user submitting the entry
    """
    try:
        db_path = os.path.join(os.path.dirname(__file__), "diary.db")
        
        # Validate entry data - only require date and content
        if not all(key in entry for key in ["date", "content"]):
            st.error("❌ Missing required fields: date, content")
            return False
            
        if not entry["content"].strip():
            st.error("❌ Content cannot be empty")
            return False
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ensure table exists with user_id column
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add user_id column if it doesn't exist (migration)
        try:
            cursor.execute("ALTER TABLE diary_entries ADD COLUMN user_id INTEGER DEFAULT 1")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Insert entry with user isolation
        cursor.execute("""
            INSERT INTO diary_entries (user_id, date, content, tags) 
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            entry["date"],
            entry["content"],
            entry.get("tags", "")
        ))
        
        conn.commit()
        entry_id = cursor.lastrowid
        conn.close()
        
        st.success(f"✅ Diary entry saved to local database! (ID: {entry_id})")
        return True
        
    except sqlite3.Error as e:
        st.error(f"❌ Database Error: {str(e)}")
        return False
    except Exception as e:
        st.error(f"❌ Unexpected Error: {str(e)}")
        return False

def submit_text_to_database_api(entry: Dict[str, Any]) -> bool:
    """
    Submit diary entry via FastAPI v3 with authentication.
    
    Args:
        entry: Dictionary containing diary entry data
    """
    try:
        # For debug server (port 8004), skip authentication
        if "8004" in API_BASE_URL:
            # Validate entry data for debug mode
            if not all(key in entry for key in ["date", "content"]):
                st.error("❌ Missing required fields: date, content")
                return False
                
            if not entry["content"].strip():
                st.error("❌ Content cannot be empty")
                return False
            
            # Prepare payload for debug server
            payload = {
                "date": entry["date"],
                "content": entry["content"],
                "tags": entry.get("tags", "")
            }
            
            headers = {"Content-Type": "application/json"}
            
        else:
            # Check if user is authenticated for production servers
            if not hasattr(st.session_state, 'session_token') or not st.session_state.session_token:
                st.error("❌ Please login first to save diary entries")
                return False
            
            # Validate entry data
            if not all(key in entry for key in ["date", "content"]):
                st.error("❌ Missing required fields: date, content")
                return False
                
            if not entry["content"].strip():
                st.error("❌ Content cannot be empty")
                return False
            
            # Prepare payload for production API (no title field)
            payload = {
                "date": entry["date"],
                "content": entry["content"],
                "tags": entry.get("tags", "")
            }
            
            # Get authentication headers
            headers = get_auth_headers()
            headers["Content-Type"] = "application/json"
        
        # Submit to FastAPI v3
        response = requests.post(
            f"{API_BASE_URL}/diary/entries",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            st.success(f"✅ Diary entry saved successfully! (ID: {result.get('id', 'N/A')})")
            return True
        elif response.status_code == 401:
            st.error("❌ Authentication failed. Please login again.")
            return False
        elif response.status_code == 422:
            st.error("❌ Invalid data format. Please check your entry.")
            return False
        else:
            st.error(f"❌ Failed to save diary entry. Status code: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Connection Error: {str(e)}")
        return False
    except Exception as e:
        st.error(f"❌ Unexpected Error: {str(e)}")
        return False
        
        # Submit to FastAPI v3
        response = requests.post(
            f"{API_BASE_URL}/diary/entries",
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            st.success(f"✅ Diary entry saved successfully! (ID: {result.get('id', 'N/A')})")
            return True
        elif response.status_code == 401:
            st.error("❌ Authentication failed. Please login again.")
            # Clear session token safely
            if hasattr(st.session_state, 'session_token'):
                try:
                    del st.session_state.session_token
                except Exception:
                    st.session_state.session_token = None
            return False
        else:
            try:
                error_detail = response.json().get('detail', 'Unknown error')
            except:
                error_detail = response.text
            st.error(f"❌ API Error: {response.status_code} - {error_detail}")
            return False
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Make sure FastAPI server is running on http://127.0.0.1:8000")
        return False
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Connection Error: {str(e)}")
        return False

def submit_text_to_database(entry: Dict[str, Any], user_id: int = None) -> bool:
    """
    Submit diary entry to database. Try API first, fallback to direct database access.
    
    Args:
        entry: Dictionary containing diary entry data
        user_id: ID of the user (used for direct database access fallback)
    """
    # Get user_id from session state if not provided
    if user_id is None:
        user_id = getattr(st.session_state, 'current_user_id', 1)
    
    # Try API first
    if check_api_connection():
        if submit_text_to_database_api(entry):
            return True
        st.warning("⚠️ API submission failed, trying direct database access...")
    else:
        st.warning("⚠️ API not available, using direct database access...")
    
    # Fallback to direct database access
    return submit_text_to_database_direct(entry, user_id)

def load_entries_from_database_api() -> List[Dict[str, Any]]:
    """
    Load diary entries from FastAPI v2 with authentication.
    """
    try:
        # Check if user is authenticated
        if not hasattr(st.session_state, 'session_token') or not st.session_state.session_token:
            st.error("❌ Please login first to load diary entries")
            return []
        
        # Get authentication headers
        headers = get_auth_headers()
        
        # Load from FastAPI v2
        response = requests.get(
            f"{API_BASE_URL}/diary/entries",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            entries = response.json()
            st.success(f"✅ Loaded {len(entries)} entries from API")
            return entries
        elif response.status_code == 401:
            st.error("❌ Authentication failed. Please login again.")
            # Clear session token safely
            if hasattr(st.session_state, 'session_token'):
                try:
                    del st.session_state.session_token
                except Exception:
                    st.session_state.session_token = None
            return []
        else:
            try:
                error_detail = response.json().get('detail', 'Unknown error')
            except:
                error_detail = response.text
            st.error(f"❌ API Error: {response.status_code} - {error_detail}")
            return []
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Connection Error: {str(e)}")
        return []

def load_entries_from_database_direct(user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Load diary entries directly from SQLite database with user isolation.
    
    Args:
        user_id: ID of the user to load entries for
    """
    try:
        db_path = os.path.join(os.path.dirname(__file__), "diary.db")
        
        if not os.path.exists(db_path):
            st.warning("⚠️ Database not found. No entries to load.")
            return []
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()
        
        # Load entries for specific user only
        cursor.execute("""
            SELECT * FROM diary_entries 
            WHERE user_id = ? 
            ORDER BY date DESC, created_at DESC
        """, (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        entries = []
        for row in rows:
            entries.append({
                "id": row["id"],
                "user_id": row["user_id"],
                "date": row["date"],
                "content": row["content"],
                "tags": row["tags"] or "",
                "created_at": row["created_at"]
            })
        
        st.success(f"✅ Loaded {len(entries)} entries from local database for user {user_id}")
        return entries
        
    except sqlite3.Error as e:
        st.error(f"❌ Database Error: {str(e)}")
        return []
    except Exception as e:
        st.error(f"❌ Unexpected Error: {str(e)}")
        return []

def load_entries_from_database(user_id: int = None) -> List[Dict[str, Any]]:
    """
    Load diary entries from database. Try API first, fallback to direct database access.
    
    Args:
        user_id: ID of the user (used for direct database access fallback)
    """
    # Get user_id from session state if not provided
    if user_id is None:
        user_id = getattr(st.session_state, 'current_user_id', 1)
    
    # Try API first
    if check_api_connection():
        entries = load_entries_from_database_api()
        if entries:  # If API worked and returned data
            return entries
        st.warning("⚠️ API load failed, trying direct database access...")
    else:
        st.warning("⚠️ API not available, using direct database access...")
    
    # Fallback to direct database access
    return load_entries_from_database_direct(user_id)

def delete_diary_entry_api(entry_id: int) -> bool:
    """
    Delete diary entry via FastAPI v2 with authentication.
    
    Args:
        entry_id: ID of the entry to delete
    """
    try:
        # Check if user is authenticated
        if not hasattr(st.session_state, 'session_token') or not st.session_state.session_token:
            st.error("❌ Please login first to delete diary entries")
            return False
        
        # Get authentication headers
        headers = get_auth_headers()
        
        # Delete via FastAPI v2
        response = requests.delete(
            f"{API_BASE_URL}/diary/entries/{entry_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            st.success("✅ Diary entry deleted successfully!")
            return True
        elif response.status_code == 401:
            st.error("❌ Authentication failed. Please login again.")
            return False
        elif response.status_code == 404:
            st.error("❌ Diary entry not found or you don't have permission to delete it")
            return False
        else:
            try:
                error_detail = response.json().get('detail', 'Unknown error')
            except:
                error_detail = response.text
            st.error(f"❌ API Error: {response.status_code} - {error_detail}")
            return False
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API")
        return False
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Connection Error: {str(e)}")
        return False

def delete_diary_entry_direct(entry_id: int, user_id: int = 1) -> bool:
    """
    Delete diary entry directly from SQLite database with user isolation.
    
    Args:
        entry_id: ID of the entry to delete
        user_id: ID of the user (for security - can only delete own entries)
    """
    try:
        db_path = os.path.join(os.path.dirname(__file__), "diary.db")
        
        if not os.path.exists(db_path):
            st.error("❌ Database not found")
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Delete entry only if it belongs to the user
        cursor.execute("""
            DELETE FROM diary_entries 
            WHERE id = ? AND user_id = ?
        """, (entry_id, user_id))
        
        if cursor.rowcount == 0:
            st.error("❌ Entry not found or you don't have permission to delete it")
            conn.close()
            return False
        
        conn.commit()
        conn.close()
        
        st.success("✅ Diary entry deleted successfully!")
        return True
        
    except sqlite3.Error as e:
        st.error(f"❌ Database Error: {str(e)}")
        return False
    except Exception as e:
        st.error(f"❌ Unexpected Error: {str(e)}")
        return False

def delete_diary_entry(entry_id: int, user_id: int = None) -> bool:
    """
    Delete diary entry from database. Try API first, fallback to direct database access.
    
    Args:
        entry_id: ID of the entry to delete
        user_id: ID of the user (used for direct database access fallback)
    """
    # Get user_id from session state if not provided
    if user_id is None:
        user_id = getattr(st.session_state, 'current_user_id', 1)
    
    # Try API first
    if check_api_connection():
        if delete_diary_entry_api(entry_id):
            return True
        st.warning("⚠️ API deletion failed, trying direct database access...")
    else:
        st.warning("⚠️ API not available, using direct database access...")
    
    # Fallback to direct database access
    return delete_diary_entry_direct(entry_id, user_id)
