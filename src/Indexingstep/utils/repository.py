"""
Repository for diary entries with user isolation.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional
import logging

from models import DiaryEntry, IndexingConfig
from database_utils import open_db, ensure_database_exists, migrate_user_data

logger = logging.getLogger(__name__)


class DiaryRepository:
    """Repository for managing diary entries with user isolation."""
    
    def __init__(self, config: IndexingConfig):
        """
        Initialize repository.
        
        Args:
            config: Indexing configuration
        """
        self.config = config
        self.user_id = config.user_id
        self._ensure_database()
    
    def _ensure_database(self) -> None:
        """Ensure user database exists and migrate data if needed."""
        ensure_database_exists(self.config.user_db_path, self.user_id)
        
        # Try to migrate data from shared database
        migrated = migrate_user_data(
            self.config.fallback_db_path,
            self.config.user_db_path,
            self.user_id
        )
        
        if migrated > 0:
            logger.info(f"[user={self.user_id}] Migrated {migrated} entries from shared database")
    
    def get_entries_count(self) -> int:
        """Get total number of entries for this user."""
        try:
            with open_db(self.config.user_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM diary_entries WHERE user_id = ?", (self.user_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"[user={self.user_id}] Failed to get entries count: {e}")
            return 0
    
    def load_all_entries(self) -> List[DiaryEntry]:
        """Load all diary entries for this user."""
        try:
            with open_db(self.config.user_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, date, content, tags, created_at 
                    FROM diary_entries 
                    WHERE user_id = ?
                    ORDER BY date DESC, created_at DESC
                """, (self.user_id,))
                
                rows = cursor.fetchall()
                entries = []
                
                for row in rows:
                    entries.append(DiaryEntry(
                        id=row['id'],
                        user_id=row['user_id'],
                        date=row['date'],
                        content=row['content'],
                        tags=row['tags'] or '',
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
                    ))
                
                logger.info(f"[user={self.user_id}] Loaded {len(entries)} total entries")
                return entries
                
        except Exception as e:
            logger.error(f"[user={self.user_id}] Failed to load all entries: {e}")
            return []
    
    def load_incremental_entries(self, since: datetime) -> List[DiaryEntry]:
        """
        Load diary entries created after the given timestamp.
        
        Args:
            since: Load entries created after this timestamp
            
        Returns:
            List of diary entries
        """
        try:
            with open_db(self.config.user_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, user_id, date, content, tags, created_at 
                    FROM diary_entries 
                    WHERE user_id = ? AND created_at > ?
                    ORDER BY date DESC, created_at DESC
                """, (self.user_id, since.isoformat()))
                
                rows = cursor.fetchall()
                entries = []
                
                for row in rows:
                    entries.append(DiaryEntry(
                        id=row['id'],
                        user_id=row['user_id'],
                        date=row['date'],
                        content=row['content'],
                        tags=row['tags'] or '',
                        created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now()
                    ))
                
                logger.info(f"[user={self.user_id}] Loaded {len(entries)} entries since {since}")
                return entries
                
        except Exception as e:
            logger.error(f"[user={self.user_id}] Failed to load incremental entries: {e}")
            return []
