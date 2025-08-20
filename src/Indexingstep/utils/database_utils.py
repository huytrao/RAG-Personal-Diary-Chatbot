"""
Database utilities and context managers.
"""

import sqlite3
import os
from contextlib import contextmanager
from typing import Generator
import logging

logger = logging.getLogger(__name__)


@contextmanager
def open_db(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    
    Args:
        db_path: Path to the SQLite database
        
    Yields:
        Database connection
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error with {db_path}: {e}")
        raise
    finally:
        if conn:
            conn.close()


def ensure_database_exists(db_path: str, user_id: int) -> None:
    """
    Ensure user-specific database exists with proper schema.
    
    Args:
        db_path: Path to the database file
        user_id: User ID for default value
    """
    if os.path.exists(db_path):
        return
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    with open_db(db_path) as conn:
        cursor = conn.cursor()
        
        # Create table schema
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
        
        # Create index
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_date ON diary_entries(user_id, date)
        """)
        
        conn.commit()
        
    logger.info(f"Created user database: {db_path}")


def migrate_user_data(source_db_path: str, target_db_path: str, user_id: int) -> int:
    """
    Migrate user data from shared database to user-specific database.
    
    Args:
        source_db_path: Path to source database
        target_db_path: Path to target database
        user_id: User ID to migrate
        
    Returns:
        Number of entries migrated
    """
    if not os.path.exists(source_db_path):
        return 0
    
    migrated_count = 0
    
    try:
        with open_db(source_db_path) as source_conn:
            with open_db(target_db_path) as target_conn:
                source_cursor = source_conn.cursor()
                target_cursor = target_conn.cursor()
                
                # Check if shared DB has user_id column
                source_cursor.execute("PRAGMA table_info(diary_entries)")
                columns = [col[1] for col in source_cursor.fetchall()]
                
                if 'user_id' in columns:
                    # Migrate specific user data
                    source_cursor.execute("""
                        SELECT date, content, tags, created_at 
                        FROM diary_entries 
                        WHERE user_id = ?
                    """, (user_id,))
                else:
                    # If no user_id column, migrate all data to user 1 only
                    if user_id == 1:
                        source_cursor.execute("""
                            SELECT date, content, COALESCE(tags, ''), created_at 
                            FROM diary_entries
                        """)
                    else:
                        return 0
                
                rows = source_cursor.fetchall()
                
                for row in rows:
                    target_cursor.execute("""
                        INSERT OR IGNORE INTO diary_entries (user_id, date, content, tags, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, row[0], row[1], row[2] if len(row) > 2 else '', row[3] if len(row) > 3 else None))
                
                target_conn.commit()
                migrated_count = len(rows)
        
        if migrated_count > 0:
            logger.info(f"Migrated {migrated_count} entries for user {user_id}")
    
    except Exception as e:
        logger.warning(f"Could not migrate data for user {user_id}: {e}")
    
    return migrated_count
