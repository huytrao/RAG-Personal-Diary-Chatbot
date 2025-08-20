"""
Auto-Sync Module for RAG Personal Diary Chatbot
Handles automatic synchronization between database and vector store
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import streamlit as st

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Indexingstep'))
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from pipeline import DiaryIndexingPipeline
    from embedding_and_storing import DiaryEmbeddingAndStorage
    from run_user_indexing import UserIsolatedIndexingPipeline
except ImportError as e:
    logging.error(f"Could not import indexing modules: {e}")
    DiaryIndexingPipeline = None
    DiaryEmbeddingAndStorage = None
    UserIsolatedIndexingPipeline = None

class AutoSyncManager:
    """Manages automatic synchronization between SQL database and vector database"""
    
    def __init__(self, user_id: int = 1):
        self.user_id = user_id
        # Use user-specific database path
        self.db_path = os.path.join(os.path.dirname(__file__), "backend", f"user_{user_id}_diary.db")
        self.vector_db_path = os.path.join(os.path.dirname(__file__), "..", "Indexingstep", f"user_{user_id}_vector_db")
        self.collection_name = f"user_{user_id}_diary_entries"
        
        # Load API key
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'Indexingstep', '.env'))
        self.api_key = os.getenv("GOOGLE_API_KEY")
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def get_last_sync_time(self) -> Optional[datetime]:
        """Get the last sync timestamp from a tracking file"""
        sync_file = os.path.join(os.path.dirname(__file__), f"last_sync_user_{self.user_id}.txt")
        try:
            if os.path.exists(sync_file):
                with open(sync_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            self.logger.warning(f"Could not read last sync time: {e}")
        return None
    
    def update_last_sync_time(self, timestamp: datetime = None):
        """Update the last sync timestamp"""
        if timestamp is None:
            timestamp = datetime.now()
        
        sync_file = os.path.join(os.path.dirname(__file__), f"last_sync_user_{self.user_id}.txt")
        try:
            with open(sync_file, 'w') as f:
                f.write(timestamp.isoformat())
        except Exception as e:
            self.logger.warning(f"Could not update last sync time: {e}")
    
    def get_changed_entries(self, since: Optional[datetime] = None) -> Dict[str, List]:
        """Get entries that changed since the last sync"""
        if since is None:
            since = self.get_last_sync_time()
            if since is None:
                since = datetime.now() - timedelta(days=7)  # Default to last week
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get new/updated entries
            since_str = since.strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                SELECT id, date, content, created_at, tags 
                FROM diary_entries 
                WHERE user_id = ? AND created_at > ?
                ORDER BY created_at DESC
            """, (self.user_id, since_str))
            
            new_entries = []
            for row in cursor.fetchall():
                new_entries.append({
                    'id': row[0],
                    'date': row[1], 
                    'content': row[2],
                    'created_at': row[3],
                    'tags': row[4] or ''
                })
            
            conn.close()
            
            return {
                'new_entries': new_entries,
                'deleted_entries': []  # TODO: Implement deletion tracking
            }
            
        except Exception as e:
            self.logger.error(f"Error getting changed entries: {e}")
            return {'new_entries': [], 'deleted_entries': []}
    
    def auto_index_new_entries(self, entries: List[Dict]) -> bool:
        """Automatically index new entries"""
        if not entries or not self.api_key:
            return True
            
        try:
            # Run incremental indexing for new entries
            config = {
                "google_api_key": self.api_key,
                "db_path": self.db_path,
                "persist_directory": self.vector_db_path,
                "collection_name": self.collection_name,
                "embedding_model": "models/embedding-001",
                "chunk_size": 800,
                "chunk_overlap": 100,
                "batch_size": 50
            }
            
            # Get date range for new entries
            if entries:
                dates = [entry['date'] for entry in entries]
                start_date = min(dates)
                end_date = max(dates)
                
            # Use the USER-ISOLATED indexing approach
            if UserIsolatedIndexingPipeline:
                pipeline = UserIsolatedIndexingPipeline(
                    user_id=self.user_id,
                    google_api_key=config["google_api_key"],
                    base_db_path=os.path.dirname(config["db_path"]),
                    base_persist_directory=os.path.dirname(config["persist_directory"]),
                    embedding_model=config["embedding_model"],
                    chunk_size=config["chunk_size"],
                    chunk_overlap=config["chunk_overlap"],
                    batch_size=config["batch_size"]
                )
                
                # Run incremental indexing
                success = pipeline.run_incremental_indexing()
                
                if success:
                    self.logger.info(f"Successfully indexed {len(entries)} new entries")
                    return True
                else:
                    self.logger.warning(f"Indexing completed with warnings")
                    return False
            else:
                # Fallback to basic pipeline if UserIsolatedIndexingPipeline not available
                self.logger.warning("UserIsolatedIndexingPipeline not available, falling back to basic pipeline")
                if DiaryIndexingPipeline:
                    pipeline = DiaryIndexingPipeline()
                    pipeline.run()
                    return True
                else:
                    self.logger.error("No indexing pipeline available")
                    return False
            
        except Exception as e:
            self.logger.error(f"Error auto-indexing new entries: {e}")
            return False
        
        return True
    
    def auto_remove_deleted_entries(self, deleted_entry_ids: List[int]) -> bool:
        """Automatically remove deleted entries from vector database"""
        if not deleted_entry_ids or not self.api_key:
            return True
            
        try:
            embedding_storage = DiaryEmbeddingAndStorage(
                user_id=self.user_id,
                api_key=self.api_key,
                base_persist_directory=os.path.dirname(self.vector_db_path),
                embedding_model="models/embedding-001"
            )
            
            # Remove each deleted entry
            for entry_id in deleted_entry_ids:
                filter_criteria = {"entry_id": str(entry_id)}
                success = embedding_storage.delete_documents_by_metadata(filter_criteria)
                self.logger.info(f"Removed entry {entry_id} from vector DB: {success}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing deleted entries: {e}")
            return False
    
    def run_sync(self) -> Dict[str, Any]:
        """
        Run the complete synchronization process and return results.
        This is the main entry point to be called from the UI.
        """
        self.logger.info(f"🚀 Starting sync for user {self.user_id}...")
        results = {'status': 'failed', 'indexed_count': 0, 'deleted_count': 0, 'error': None}
        
        try:
            # 1. Get changes from the database
            last_sync_time = self.get_last_sync_time()
            self.logger.info(f"Last sync time: {last_sync_time}")
            
            changed_data = self.get_changed_entries(last_sync_time)
            new_entries = changed_data.get('new_entries', [])
            # deleted_ids = changed_data.get('deleted_entries', []) # Deletion not implemented yet
            
            self.logger.info(f"Found {len(new_entries)} new entries to index.")
            
            if not new_entries:
                results['status'] = 'success'
                results['message'] = "No new entries to index."
                self.logger.info("✅ Sync finished: No new entries.")
                self.update_last_sync_time() # Update sync time even if no changes
                return results

            # 2. Index new entries
            index_success = self.auto_index_new_entries(new_entries)
            if not index_success:
                raise RuntimeError("Failed to index new entries.")
            
            results['indexed_count'] = len(new_entries)
            
            # 3. Update last sync time
            self.update_last_sync_time()
            
            results['status'] = 'success'
            results['message'] = f"Successfully indexed {len(new_entries)} new entries."
            self.logger.info(f"✅ Sync successful for user {self.user_id}.")
            
        except Exception as e:
            self.logger.error(f"❌ Sync failed for user {self.user_id}: {e}", exc_info=True)
            results['error'] = str(e)
            
        return results

    def perform_auto_sync(self) -> Dict[str, Any]:
        """Perform automatic synchronization"""
        try:
            # Get changes since last sync
            changes = self.get_changed_entries()
            new_entries = changes['new_entries']
            deleted_entries = changes['deleted_entries']
            
            results = {
                'success': True,
                'new_entries_count': len(new_entries),
                'deleted_entries_count': len(deleted_entries),
                'errors': []
            }
            
            # Index new entries
            if new_entries:
                index_success = self.auto_index_new_entries(new_entries)
                if not index_success:
                    results['errors'].append("Failed to index some new entries")
            
            # Remove deleted entries
            if deleted_entries:
                delete_success = self.auto_remove_deleted_entries(deleted_entries)
                if not delete_success:
                    results['errors'].append("Failed to remove some deleted entries")
            
            # Update sync timestamp
            self.update_last_sync_time()
            
            results['success'] = len(results['errors']) == 0
            return results
            
        except Exception as e:
            self.logger.error(f"Auto-sync failed: {e}")
            return {
                'success': False,
                'new_entries_count': 0,
                'deleted_entries_count': 0,
                'errors': [str(e)]
            }

# Streamlit helper functions
def run_auto_sync(user_id: int = None) -> bool:
    """Run auto-sync and show results in Streamlit"""
    if user_id is None:
        user_id = getattr(st.session_state, 'current_user_id', 1)
    
    try:
        # Simple approach: call the indexing script directly
        import subprocess
        
        script_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'Indexingstep', 
            'run_user_indexing.py'
        )
        
        if not os.path.exists(script_path):
            return False
        
        # Get virtual environment python
        venv_python = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            '..', 
            '.venv', 
            'Scripts', 
            'python.exe'
        )
        
        python_cmd = venv_python if os.path.exists(venv_python) else sys.executable
        
        # Run incremental indexing for the user
        result = subprocess.run(
            [python_cmd, script_path, '--user-id', str(user_id)],
            cwd=os.path.dirname(script_path),
            capture_output=True,
            text=True,
            timeout=120  # 2 minutes timeout
        )
        
        if result.returncode == 0:
            return True
        else:
            return False
            
    except Exception as e:
        return False
        
def run_auto_sync_legacy(user_id: int = None) -> bool:
    """Legacy auto-sync using the AutoSyncManager class"""
    if user_id is None:
        user_id = getattr(st.session_state, 'current_user_id', 1)
    
    try:
        sync_manager = AutoSyncManager(user_id)
        results = sync_manager.perform_auto_sync()
        
        if results['success']:
            if results['new_entries_count'] > 0:
                st.success(f"✅ Auto-sync: {results['new_entries_count']} new entries indexed")
            return True
        else:
            st.warning(f"⚠️ Auto-sync completed with warnings: {', '.join(results['errors'])}")
            return True
            
    except Exception as e:
        st.warning(f"⚠️ Auto-sync failed: {str(e)}")
        return False

def schedule_auto_sync():
    """Schedule auto-sync to run periodically"""
    # This could be enhanced with background tasks or scheduled jobs
    # For now, we'll call it manually when entries are created/deleted
    pass
