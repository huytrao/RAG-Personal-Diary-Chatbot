"""
Data models for the indexing pipeline.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class DiaryEntry:
    """Represents a diary entry from the database."""
    id: int
    user_id: int
    date: str
    content: str
    tags: str
    created_at: datetime

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiaryEntry':
        """Create DiaryEntry from dictionary."""
        return cls(
            id=data['id'],
            user_id=data['user_id'],
            date=data['date'],
            content=data['content'],
            tags=data.get('tags', ''),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at']
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'date': self.date,
            'content': self.content,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at
        }


@dataclass
class DiaryChunk:
    """Represents a processed chunk of diary content."""
    entry_id: int
    user_id: int
    chunk_id: str
    text: str
    metadata: Dict[str, Any]

    @classmethod
    def from_entry_and_text(cls, entry: DiaryEntry, text: str, chunk_index: int) -> 'DiaryChunk':
        """Create DiaryChunk from entry and text."""
        chunk_id = f"{entry.id}_{chunk_index}"
        metadata = {
            'entry_id': entry.id,
            'user_id': entry.user_id,
            'date': entry.date,
            'tags': entry.tags,
            'chunk_index': chunk_index,
            'created_at': entry.created_at.isoformat() if isinstance(entry.created_at, datetime) else entry.created_at
        }
        
        return cls(
            entry_id=entry.id,
            user_id=entry.user_id,
            chunk_id=chunk_id,
            text=text,
            metadata=metadata
        )


@dataclass
class IndexingConfig:
    """Configuration for the indexing pipeline."""
    user_id: int
    google_api_key: str
    base_db_path: str = "../streamlit_app/backend/VectorDatabase"
    base_persist_directory: str = "./"
    embedding_model: str = "models/embedding-001"
    chunk_size: int = 800
    chunk_overlap: int = 100
    batch_size: int = 50
    
    @property
    def user_db_path(self) -> str:
        """Get user-specific database path."""
        return f"{self.base_db_path}/user_{self.user_id}_diary.db"
    
    @property
    def fallback_db_path(self) -> str:
        """Get fallback database path."""
        return f"{self.base_db_path}/diary.db"
    
    @property
    def vector_db_path(self) -> str:
        """Get user-specific vector database path."""
        return f"{self.base_persist_directory}/user_{self.user_id}_vector_db"
    
    @property
    def collection_name(self) -> str:
        """Get collection name for this user."""
        return f"user_{self.user_id}_diary_entries"


@dataclass
class IndexingStats:
    """Statistics about indexing status."""
    user_id: int
    database_entries: int
    vector_documents: int
    last_sync: Optional[datetime]
    vector_db_path: str
    database_path: str
    error: Optional[str] = None
