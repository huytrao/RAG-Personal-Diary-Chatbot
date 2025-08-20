import requests
import streamlit as st
import sqlite3
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

# API configuration
API_BASE_URL = "http://127.0.0.1:8004"

def get_user_database_path(user_id: int) -> str:
    """Get the path to user-specific database"""
    base_path = os.path.dirname(__file__)
    return os.path.join(base_path, f"user_{user_id}_diary.db")

def get_fallback_database_path() -> str:
    """Get the                    # Run sync to update vector database after deletion
                    sync_results = sync_manager.run_sync()
                    
                    indexed_count = sync_results.get('indexed_count', 0)
                    if indexed_count > 0:
                        st.info(f"🔍 Search index rebuilt with {indexed_count} remaining entries.")
                        
                        # Update RAG system if loaded
                        if hasattr(st.session_state, 'rag_system') and st.session_state.rag_system:
                            try:
                                reloaded_count = st.session_state.rag_system.reload_vector_store()
                                st.session_state.document_count = reloaded_count
                                st.info(f"🤖 RAG system updated with {reloaded_count} documents.")
                            except Exception as e:
                                st.warning(f"⚠️ Could not reload RAG system: {e}")
                    else:
                        st.info("✅ Search index already up-to-date.")          st.info(f"🔄 Search index updated. Indexed {indexed_count} entries.") to fallback shared database"""
    return os.path.join(os.path.dirname(__file__), "diary.db")

def ensure_user_database_exists(user_id: int) -> str:
    """Ensure user-specific database exists and return its path"""
    user_db_path = get_user_database_path(user_id)
    
    if not os.path.exists(user_db_path):
        # Create user-specific database
        conn = sqlite3.connect(user_db_path)
        cursor = conn.cursor()
        
        # Create table with proper schema
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT {user_id},
                date TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_date ON diary_entries(user_id, date)
        """)
        
        conn.commit()
        conn.close()
        
        # Try to migrate data from shared database if exists
        migrate_user_data_from_shared_db(user_id)
    
    return user_db_path

def migrate_user_data_from_shared_db(user_id: int):
    """Migrate user data from shared database to user-specific database"""
    shared_db_path = get_fallback_database_path()
    user_db_path = get_user_database_path(user_id)
    
    if not os.path.exists(shared_db_path):
        return
    
    try:
        # Connect to both databases
        shared_conn = sqlite3.connect(shared_db_path)
        user_conn = sqlite3.connect(user_db_path)
        
        shared_cursor = shared_conn.cursor()
        user_cursor = user_conn.cursor()
        
        # Check if shared DB has user_id column
        shared_cursor.execute("PRAGMA table_info(diary_entries)")
        columns = [col[1] for col in shared_cursor.fetchall()]
        
        if 'user_id' in columns:
            # Migrate specific user data
            shared_cursor.execute("""
                SELECT date, content, tags, created_at 
                FROM diary_entries 
                WHERE user_id = ?
            """, (user_id,))
        else:
            # If no user_id column, migrate all data to user 1 only
            if user_id == 1:
                shared_cursor.execute("""
                    SELECT date, content, COALESCE(tags, ''), created_at 
                    FROM diary_entries
                """)
            else:
                shared_conn.close()
                user_conn.close()
                return
        
        rows = shared_cursor.fetchall()
        
        for row in rows:
            user_cursor.execute("""
                INSERT OR IGNORE INTO diary_entries (user_id, date, content, tags, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, row[0], row[1], row[2], row[3]))
        
        user_conn.commit()
        
        shared_conn.close()
        user_conn.close()
        
        if rows:
            st.info(f"✅ Migrated {len(rows)} entries for user {user_id} from shared database")
    
    except Exception as e:
        st.warning(f"⚠️ Could not migrate data for user {user_id}: {str(e)}")

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
    Submit diary entry directly to user-specific SQLite database.
    
    Args:
        entry: Dictionary containing diary entry data
        user_id: ID of the user submitting the entry
    """
    try:
        # Ensure user database exists
        db_path = ensure_user_database_exists(user_id)
        
        # Validate entry data
        if not all(key in entry for key in ["date", "content"]):
            st.error("❌ Missing required fields: date, content")
            return False
            
        if not entry["content"].strip():
            st.error("❌ Content cannot be empty")
            return False
        
        # Connect to user database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
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
        
        st.success(f"✅ Diary entry saved to user database! (ID: {entry_id})")
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
            
            # Prepare payload for production API
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

def submit_text_to_database(entry: Dict[str, Any], user_id: int = None) -> bool:
    """
    Submit diary entry to database. Always use user-specific database.
    Automatically triggers indexing for RAG system after successful save.
    
    Args:
        entry: Dictionary containing diary entry data
        user_id: ID of the user (required for user isolation)
    """
    # Get user_id from session state if not provided
    if user_id is None:
        user_id = getattr(st.session_state, 'current_user_id', 1)
    
    # Submit to database first
    success = submit_text_to_database_direct(entry, user_id)
    
    # If save successful, trigger auto-sync for RAG indexing
    if success:
        try:
            # Import auto_sync here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from auto_sync import AutoSyncManager
            
            # Trigger auto-sync in background
            with st.spinner("🔄 Auto-syncing with search index..."):
                sync_manager = AutoSyncManager(user_id=user_id)
                sync_results = sync_manager.run_sync()
                
                indexed_count = sync_results.get('indexed_count', 0)
                if indexed_count > 0:
                    st.info(f"🔍 Auto-indexed {indexed_count} new item(s). Entry is now searchable!")
                    
                    # Update RAG system if loaded
                    if hasattr(st.session_state, 'rag_system') and st.session_state.rag_system:
                        try:
                            reloaded_count = st.session_state.rag_system.reload_vector_store()
                            st.session_state.document_count = reloaded_count
                            st.info(f"🤖 RAG system updated with {reloaded_count} documents.")
                        except Exception as e:
                            st.warning(f"⚠️ Could not reload RAG system: {e}")
                else:
                    st.info("✅ Search index already up-to-date.")
                    
        except ImportError:
            st.warning("⚠️ Auto-sync module not available. Entry saved but not indexed.")
        except Exception as e:
            st.warning(f"⚠️ Auto-sync failed: {e}. Entry saved but may not be searchable immediately.")
    
    return success

def load_entries_from_database_direct(user_id: int = 1) -> List[Dict[str, Any]]:
    """
    Load diary entries directly from user-specific SQLite database.
    
    Args:
        user_id: ID of the user to load entries for
    """
    try:
        # Ensure user database exists
        db_path = ensure_user_database_exists(user_id)
        
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
        
        # Only show success message if entries found
        if entries:
            st.success(f"✅ Loaded {len(entries)} entries for user {user_id}")
        else:
            st.info(f"ℹ️ No diary entries found for user {user_id}")
        
        return entries
        
    except sqlite3.Error as e:
        st.error(f"❌ Database Error: {str(e)}")
        return []
    except Exception as e:
        st.error(f"❌ Unexpected Error: {str(e)}")
        return []

def load_entries_from_database(user_id: int = None) -> List[Dict[str, Any]]:
    """
    Load diary entries from user-specific database.
    
    Args:
        user_id: ID of the user (required for user isolation)
    """
    # Get user_id from session state if not provided
    if user_id is None:
        user_id = getattr(st.session_state, 'current_user_id', 1)
    
    # Always use direct database access for user isolation
    return load_entries_from_database_direct(user_id)

def delete_diary_entry_direct(entry_id: int, user_id: int = 1) -> bool:
    """
    Delete diary entry directly from user-specific SQLite database.
    
    Args:
        entry_id: ID of the entry to delete
        user_id: ID of the user (for security - can only delete own entries)
    """
    try:
        # Ensure user database exists
        db_path = ensure_user_database_exists(user_id)
        
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
    Delete diary entry from user-specific database and vectordatabase of RAG indexing.
    Automatically removes entry from vector database (search index) after successful deletion.
    updated # If save successful, trigger auto-sync for RAG indexing
    
    Args:
        entry_id: ID of the entry to delete
        user_id: ID of the user (required for user isolation)
    """
    # Get user_id from session state if not provided
    if user_id is None:
        user_id = getattr(st.session_state, 'current_user_id', 1)
    
    # Delete from database first
    success = delete_diary_entry_direct(entry_id, user_id)
    
    # If deletion successful, trigger auto-sync for RAG indexing
    if success:
        try:
            # Import auto_sync here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(__file__)))
            from auto_sync import AutoSyncManager
            
            # Trigger auto-sync in background to update vector database
            with st.spinner("🔄 Updating search index..."):
                sync_manager = AutoSyncManager(user_id=user_id)
                sync_results = sync_manager.run_sync()
                
                # Check if vector database was updated
                indexed_count = sync_results.get('indexed_count', 0)
                deleted_count = sync_results.get('deleted_count', 0)
                
                if deleted_count > 0:
                    st.info(f"🗑️ Removed {deleted_count} item(s) from search index.")
                if indexed_count > 0:
                    st.info(f"🔍 Auto-indexed {indexed_count} item(s) to keep search index current.")
                
                # Update RAG system if loaded
                if hasattr(st.session_state, 'rag_system') and st.session_state.rag_system:
                    try:
                        reloaded_count = st.session_state.rag_system.reload_vector_store()
                        st.session_state.document_count = reloaded_count
                        st.info(f"🤖 RAG system updated with {reloaded_count} documents.")
                    except Exception as e:
                        st.warning(f"⚠️ Could not reload RAG system: {e}")
                        
        except ImportError:
            st.warning("⚠️ Auto-sync module not available. Entry deleted but vector index not updated.")
        except Exception as e:
            st.warning(f"⚠️ Auto-sync failed: {e}. Entry deleted but vector index may be out of sync.")
    
    return success 

def get_user_database_stats(user_id: int) -> Dict[str, Any]:
    """Get statistics about user's database"""
    try:
        db_path = get_user_database_path(user_id)
        
        if not os.path.exists(db_path):
            return {"exists": False, "entries": 0, "size": 0}
        
        # Get file size
        file_size = os.path.getsize(db_path)
        
        # Get entry count
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM diary_entries WHERE user_id = ?", (user_id,))
        entry_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "exists": True,
            "entries": entry_count,
            "size": file_size,
            "path": db_path
        }
    except Exception as e:
        return {"exists": False, "entries": 0, "size": 0, "error": str(e)}

# Utility functions for debugging
def debug_user_databases():
    """Debug function to show all user databases"""
    base_path = os.path.dirname(__file__)
    
    st.write("### User Database Debug Info")
    
    # Check for user-specific databases
    user_dbs = []
    for file in os.listdir(base_path):
        if file.startswith("user_") and file.endswith("_diary.db"):
            user_id = file.replace("user_", "").replace("_diary.db", "")
            try:
                user_id_int = int(user_id)
                stats = get_user_database_stats(user_id_int)
                user_dbs.append((user_id_int, stats))
            except ValueError:
                continue
    
    if user_dbs:
        for user_id, stats in sorted(user_dbs):
            st.write(f"**User {user_id}**: {stats['entries']} entries, {stats['size']} bytes")
    else:
        st.write("No user-specific databases found")
    
    # Check shared database
    shared_db = get_fallback_database_path()
    if os.path.exists(shared_db):
        try:
            conn = sqlite3.connect(shared_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM diary_entries")
            count = cursor.fetchone()[0]
            conn.close()
            st.write(f"**Shared Database**: {count} entries")
        except Exception as e:
            st.write(f"**Shared Database**: Error - {str(e)}")
    else:
        st.write("**Shared Database**: Not found")
