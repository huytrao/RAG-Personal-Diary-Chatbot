"""
Basic tests for the refactored indexing pipeline.
"""

import unittest
import tempfile
import os
import shutil
from datetime import datetime

# Import modules to test
from models import DiaryEntry, DiaryChunk, IndexingConfig, IndexingStats
from repository import DiaryRepository
from sync_state import SyncStateStore
from database_utils import ensure_database_exists, open_db


class TestModels(unittest.TestCase):
    """Test data models."""
    
    def test_diary_entry_creation(self):
        """Test DiaryEntry creation and conversion."""
        entry = DiaryEntry(
            id=1,
            user_id=1,
            date="2025-08-20",
            content="Test diary entry",
            tags="test,personal",
            created_at=datetime.now()
        )
        
        self.assertEqual(entry.id, 1)
        self.assertEqual(entry.user_id, 1)
        self.assertEqual(entry.content, "Test diary entry")
    
    def test_diary_entry_from_dict(self):
        """Test DiaryEntry creation from dictionary."""
        data = {
            'id': 1,
            'user_id': 1,
            'date': '2025-08-20',
            'content': 'Test content',
            'tags': 'test',
            'created_at': '2025-08-20T10:00:00'
        }
        
        entry = DiaryEntry.from_dict(data)
        self.assertEqual(entry.id, 1)
        self.assertEqual(entry.content, 'Test content')
        self.assertIsInstance(entry.created_at, datetime)
    
    def test_diary_chunk_creation(self):
        """Test DiaryChunk creation from entry."""
        entry = DiaryEntry(
            id=1,
            user_id=1,
            date="2025-08-20",
            content="Test diary entry with some content",
            tags="test",
            created_at=datetime.now()
        )
        
        chunk = DiaryChunk.from_entry_and_text(entry, "Test chunk text", 0)
        
        self.assertEqual(chunk.entry_id, 1)
        self.assertEqual(chunk.user_id, 1)
        self.assertEqual(chunk.text, "Test chunk text")
        self.assertEqual(chunk.chunk_id, "1_0")
        self.assertIn('entry_id', chunk.metadata)
    
    def test_indexing_config(self):
        """Test IndexingConfig properties."""
        config = IndexingConfig(
            user_id=1,
            google_api_key="test_key",
            base_db_path="/tmp/test"
        )
        
        self.assertEqual(config.user_id, 1)
        self.assertEqual(config.user_db_path, "/tmp/test/user_1_diary.db")
        self.assertEqual(config.collection_name, "user_1_diary_entries")


class TestDatabaseUtils(unittest.TestCase):
    """Test database utilities."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.test_db_path = os.path.join(self.test_dir, "test.db")
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_ensure_database_exists(self):
        """Test database creation."""
        ensure_database_exists(self.test_db_path, user_id=1)
        
        self.assertTrue(os.path.exists(self.test_db_path))
        
        # Check schema
        with open_db(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='diary_entries'")
            tables = cursor.fetchall()
            self.assertEqual(len(tables), 1)


class TestSyncStateStore(unittest.TestCase):
    """Test sync state management."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.sync_store = SyncStateStore(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_sync_state_operations(self):
        """Test sync state save and load."""
        user_id = 1
        test_time = datetime.now()
        
        # Initially no sync state
        self.assertIsNone(self.sync_store.get_last_sync(user_id))
        
        # Save sync state
        self.sync_store.save_last_sync(user_id, test_time)
        
        # Load sync state
        loaded_time = self.sync_store.get_last_sync(user_id)
        self.assertIsNotNone(loaded_time)
        
        # Times should be close (within 1 second due to potential precision differences)
        time_diff = abs((test_time - loaded_time).total_seconds())
        self.assertLess(time_diff, 1.0)
        
        # Clear sync state
        self.sync_store.clear_sync_state(user_id)
        self.assertIsNone(self.sync_store.get_last_sync(user_id))


class TestDiaryRepository(unittest.TestCase):
    """Test diary repository."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config = IndexingConfig(
            user_id=1,
            google_api_key="test_key",
            base_db_path=self.test_dir,
            base_persist_directory=self.test_dir
        )
        self.repository = DiaryRepository(self.config)
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_repository_initialization(self):
        """Test repository initialization creates database."""
        self.assertTrue(os.path.exists(self.config.user_db_path))
    
    def test_entries_count(self):
        """Test getting entries count."""
        count = self.repository.get_entries_count()
        self.assertEqual(count, 0)  # Should be 0 for empty database
    
    def test_load_entries(self):
        """Test loading entries (empty database)."""
        entries = self.repository.load_all_entries()
        self.assertEqual(len(entries), 0)
        
        # Test incremental load
        incremental_entries = self.repository.load_incremental_entries(datetime.now())
        self.assertEqual(len(incremental_entries), 0)


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
