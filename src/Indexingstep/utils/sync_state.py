"""
Sync state management for tracking last processed timestamps.
"""

import os
from datetime import datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class SyncStateStore:
    """Manages sync state tracking for incremental processing."""
    
    def __init__(self, base_directory: str = "./"):
        """
        Initialize sync state store.
        
        Args:
            base_directory: Directory to store sync state files
        """
        self.base_directory = base_directory
    
    def _get_sync_file_path(self, user_id: int) -> str:
        """Get path to sync state file for user."""
        return os.path.join(self.base_directory, f"last_sync_user_{user_id}.txt")
    
    def get_last_sync(self, user_id: int) -> Optional[datetime]:
        """
        Get the timestamp of the last processed entry for user.
        
        Args:
            user_id: User ID
            
        Returns:
            Last sync timestamp or None if not found
        """
        try:
            sync_file = self._get_sync_file_path(user_id)
            
            if os.path.exists(sync_file):
                with open(sync_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            logger.warning(f"[user={user_id}] Could not read last sync timestamp: {e}")
        
        return None
    
    def save_last_sync(self, user_id: int, timestamp: datetime) -> None:
        """
        Save the timestamp of the last processed entry for user.
        
        Args:
            user_id: User ID
            timestamp: Timestamp to save
        """
        try:
            sync_file = self._get_sync_file_path(user_id)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(sync_file), exist_ok=True)
            
            with open(sync_file, 'w') as f:
                f.write(timestamp.isoformat())
                
            logger.info(f"[user={user_id}] Saved last sync timestamp: {timestamp}")
        except Exception as e:
            logger.error(f"[user={user_id}] Could not save last sync timestamp: {e}")
    
    def clear_sync_state(self, user_id: int) -> None:
        """
        Clear sync state for user.
        
        Args:
            user_id: User ID
        """
        try:
            sync_file = self._get_sync_file_path(user_id)
            if os.path.exists(sync_file):
                os.remove(sync_file)
                logger.info(f"[user={user_id}] Cleared sync state")
        except Exception as e:
            logger.warning(f"[user={user_id}] Could not clear sync state: {e}")
