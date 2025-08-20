#!/usr/bin/env python3
"""
User-Isolated Incremental Indexing Orchestrator

This module contains the main orchestrator class that coordinates
the indexing pipeline using clean architecture principles.
"""

import sys
import os
from datetime import datetime
from typing import List
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import indexing modules (from parent directory)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from embedding_and_storing import DiaryEmbeddingAndStorage
from diary_text_splitter import DiaryTextSplitter

# Import clean modules (from current directory)
from models import DiaryEntry, DiaryChunk, IndexingConfig, IndexingStats
from repository import DiaryRepository
from sync_state import SyncStateStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('indexing_user.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IndexingOrchestrator:
    """
    Orchestrates the complete indexing pipeline with user isolation.
    
    This class coordinates between different components:
    - DiaryRepository for data access
    - SyncStateStore for tracking progress
    - DiaryTextSplitter for text processing
    - DiaryEmbeddingAndStorage for vector operations
    """
    
    def __init__(self, config: IndexingConfig):
        """
        Initialize the indexing orchestrator.
        
        Args:
            config: Indexing configuration
        """
        self.config = config
        self.user_id = config.user_id
        
        # Initialize components
        self.repository = DiaryRepository(config)
        self.sync_store = SyncStateStore(config.base_persist_directory)
        self.text_splitter = DiaryTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )
        self.embedding_storage = DiaryEmbeddingAndStorage(
            user_id=config.user_id,
            api_key=config.google_api_key,
            base_persist_directory=config.base_persist_directory,
            embedding_model=config.embedding_model
        )
        
        logger.info(f"[user={self.user_id}] Pipeline initialized")
    
    def _compute_latest_timestamp(self, entries: List[DiaryEntry]) -> datetime:
        """
        Compute the latest timestamp from a list of entries.
        
        Args:
            entries: List of diary entries
            
        Returns:
            Latest timestamp
        """
        if not entries:
            return datetime.now()
        
        return max(entry.created_at for entry in entries)
    
    def load_incremental_entries(self) -> List[DiaryEntry]:
        """
        Load new diary entries that need to be indexed (incremental).
        
        Returns:
            List of diary entries to process
        """
        last_sync = self.sync_store.get_last_sync(self.user_id)
        
        if last_sync:
            logger.info(f"[user={self.user_id}] Loading entries since {last_sync}")
            entries = self.repository.load_incremental_entries(last_sync)
        else:
            logger.info(f"[user={self.user_id}] No previous sync found. Loading all entries")
            entries = self.repository.load_all_entries()
        
        logger.info(f"[user={self.user_id}] Found {len(entries)} entries to process")
        return entries
    
    def load_all_entries(self) -> List[DiaryEntry]:
        """
        Load all diary entries for full reindexing.
        
        Returns:
            List of all diary entries
        """
        logger.info(f"[user={self.user_id}] Full reindex: Loading all entries")
        entries = self.repository.load_all_entries()
        logger.info(f"[user={self.user_id}] Found {len(entries)} total entries")
        return entries
    
    def process_entries(self, entries: List[DiaryEntry]) -> List[DiaryChunk]:
        """
        Process diary entries into chunks for embedding.
        
        Args:
            entries: List of diary entries
            
        Returns:
            List of processed document chunks
        """
        if not entries:
            logger.info(f"[user={self.user_id}] No entries to process")
            return []
        
        try:
            chunks = []
            
            for entry in entries:
                # Use the enhanced diary splitter with our data model
                entry_dict = entry.to_dict()
                doc_chunks = self.text_splitter.split_diary_entry(entry_dict)
                
                # Convert to our DiaryChunk model
                for i, doc_chunk in enumerate(doc_chunks):
                    chunk = DiaryChunk.from_entry_and_text(entry, doc_chunk.page_content, i)
                    chunks.append(chunk)
            
            logger.info(f"[user={self.user_id}] Processed {len(entries)} entries into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"[user={self.user_id}] Failed to process entries: {e}")
            return []
    
    def embed_and_store(self, chunks: List[DiaryChunk]) -> bool:
        """
        Embed and store document chunks in vector database.
        
        Args:
            chunks: List of processed document chunks
            
        Returns:
            Success status
        """
        if not chunks:
            logger.info(f"[user={self.user_id}] No chunks to embed and store")
            return True
        
        try:
            # Convert chunks back to documents for the embedding system
            documents = []
            for chunk in chunks:
                # Create a document-like object that the embedding system expects
                from langchain.schema import Document
                doc = Document(
                    page_content=chunk.text,
                    metadata=chunk.metadata
                )
                documents.append(doc)
            
            # Process in batches
            total_processed = 0
            batch_size = self.config.batch_size
            
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                # Embed and store batch
                doc_ids = self.embedding_storage.embed_and_store_documents(batch)
                total_processed += len(doc_ids)
                
                batch_num = i // batch_size + 1
                total_batches = (len(documents) - 1) // batch_size + 1
                
                logger.info(f"[user={self.user_id}] Processed batch {batch_num}/{total_batches}: {len(doc_ids)} documents")
            
            logger.info(f"[user={self.user_id}] Successfully embedded and stored {total_processed} documents")
            return True
            
        except Exception as e:
            logger.error(f"[user={self.user_id}] Failed to embed and store documents: {e}")
            return False
    
    def run_incremental_indexing(self) -> bool:
        """
        Run incremental indexing pipeline.
        
        Returns:
            Success status
        """
        try:
            logger.info(f"[user={self.user_id}] Starting incremental indexing")
            
            # Load new entries
            entries = self.load_incremental_entries()
            
            if not entries:
                logger.info(f"[user={self.user_id}] No new entries to process")
                return True
            
            # Process entries
            chunks = self.process_entries(entries)
            
            if not chunks:
                logger.warning(f"[user={self.user_id}] No chunks generated from entries")
                return False
            
            # Embed and store
            success = self.embed_and_store(chunks)
            
            if success:
                # Update last sync timestamp
                latest_timestamp = self._compute_latest_timestamp(entries)
                self.sync_store.save_last_sync(self.user_id, latest_timestamp)
                
                logger.info(f"[user={self.user_id}] Incremental indexing completed successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"[user={self.user_id}] Incremental indexing failed: {e}")
            return False
    
    def run_full_reindexing(self) -> bool:
        """
        Run full reindexing pipeline.
        
        Returns:
            Success status
        """
        try:
            logger.info(f"[user={self.user_id}] Starting full reindexing")
            
            # Clear existing vector database
            self.embedding_storage.clear_collection()
            
            # Load all entries
            entries = self.load_all_entries()
            
            if not entries:
                logger.info(f"[user={self.user_id}] No entries found for reindexing")
                return True
            
            # Process entries
            chunks = self.process_entries(entries)
            
            if not chunks:
                logger.warning(f"[user={self.user_id}] No chunks generated from entries")
                return False
            
            # Embed and store
            success = self.embed_and_store(chunks)
            
            if success:
                # Update last sync timestamp
                self.sync_store.save_last_sync(self.user_id, datetime.now())
                logger.info(f"[user={self.user_id}] Full reindexing completed successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"[user={self.user_id}] Full reindexing failed: {e}")
            return False
    
    def get_indexing_stats(self) -> IndexingStats:
        """Get statistics about the indexing status."""
        try:
            # Database stats
            db_entries = self.repository.get_entries_count()
            
            # Vector database stats
            vector_info = self.embedding_storage.get_collection_info()
            vector_count = vector_info.get('document_count', 0)
            
            # Last sync info
            last_sync = self.sync_store.get_last_sync(self.user_id)
            
            return IndexingStats(
                user_id=self.user_id,
                database_entries=db_entries,
                vector_documents=vector_count,
                last_sync=last_sync,
                vector_db_path=self.config.vector_db_path,
                database_path=self.config.user_db_path
            )
        except Exception as e:
            logger.error(f"[user={self.user_id}] Failed to get indexing stats: {e}")
            return IndexingStats(
                user_id=self.user_id,
                database_entries=0,
                vector_documents=0,
                last_sync=None,
                vector_db_path=self.config.vector_db_path,
                database_path=self.config.user_db_path,
                error=str(e)
            )
