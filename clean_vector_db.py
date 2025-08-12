#!/usr/bin/env python3
"""
Script to clean and reset vector database when it's out of sync with the actual database.
"""
import os
import shutil
import sqlite3
from pathlib import Path

def check_database_status():
    """Check the current database and vector database status."""
    
    # Check SQLite database
    db_path = "src/streamlit_app/backend/diary.db"
    vector_db_path = "src/Indexingstep/diary_vector_db_enhanced"
    
    print("📊 DATABASE STATUS CHECK")
    print("=" * 50)
    
    # SQLite database status
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM diary_entries")
        db_count = cursor.fetchone()[0]
        print(f"📝 SQLite Database: {db_count} entries")
        
        if db_count > 0:
            cursor.execute("SELECT id, date, LEFT(content, 50) as preview FROM diary_entries")
            entries = cursor.fetchall()
            for entry in entries:
                print(f"   - ID {entry[0]}: {entry[1]} - {entry[2]}...")
        
        conn.close()
    else:
        print("❌ SQLite Database: Not found")
        db_count = 0
    
    # Vector database status
    if os.path.exists(vector_db_path):
        print(f"📦 Vector Database: Directory exists")
        print(f"   Path: {os.path.abspath(vector_db_path)}")
        
        # Count subdirectories (collections)
        subdirs = [d for d in os.listdir(vector_db_path) if os.path.isdir(os.path.join(vector_db_path, d))]
        print(f"   Collections: {len(subdirs)} directories")
        for subdir in subdirs:
            print(f"     - {subdir}")
    else:
        print("❌ Vector Database: Directory not found")
    
    print("\n🔄 SYNCHRONIZATION STATUS")
    print("=" * 50)
    
    if db_count == 0:
        if os.path.exists(vector_db_path):
            print("⚠️  OUT OF SYNC: Database is empty but vector store exists")
            print("💡 Recommendation: Delete vector database directory")
            return False
        else:
            print("✅ SYNCHRONIZED: Both database and vector store are empty")
            return True
    else:
        print("ℹ️  Database has entries - vector store should be rebuilt")
        return False

def clean_vector_database():
    """Clean the vector database directory."""
    vector_db_path = "src/Indexingstep/diary_vector_db_enhanced"
    
    if os.path.exists(vector_db_path):
        try:
            shutil.rmtree(vector_db_path)
            print(f"🗑️  Successfully deleted: {vector_db_path}")
            return True
        except PermissionError:
            print(f"❌ Permission denied: Vector database is in use")
            print("💡 Try closing all Python processes and Streamlit app, then run again")
            return False
        except Exception as e:
            print(f"❌ Error deleting vector database: {e}")
            return False
    else:
        print(f"ℹ️  Vector database directory doesn't exist")
        return True

def main():
    """Main function to check and clean vector database."""
    print("🧹 VECTOR DATABASE CLEANUP TOOL")
    print("=" * 50)
    
    # Check current status
    is_synced = check_database_status()
    
    if not is_synced:
        print("\n🧹 CLEANING VECTOR DATABASE")
        print("=" * 50)
        
        success = clean_vector_database()
        
        if success:
            print("✅ Vector database cleaned successfully!")
            print("💡 Next steps:")
            print("   1. Run indexing pipeline if you have diary entries")
            print("   2. Or start fresh - your SQLite database is ready")
        else:
            print("❌ Failed to clean vector database")
            print("💡 Try stopping all Python processes and run again")
    else:
        print("✅ No cleanup needed - databases are synchronized")

if __name__ == "__main__":
    main()
