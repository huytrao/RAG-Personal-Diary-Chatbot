"""
Custom text splitter optimized for diary entries.
Handles entry-based chunking with smart splitting for long entries.
"""

from typing import List, Optional, Any, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import logging

logger = logging.getLogger(__name__)

class DiaryTextSplitter:
    """
    Custom text splitter optimized for diary entries.
    
    Strategy:
    1. Each diary entry = 1 chunk (for short entries)
    2. Long entries → split into 200-300 tokens with 50-token sliding window
    3. Preserve metadata across all chunks
    """
    
    def __init__(
        self,
        chunk_size: int = 300,  # ~200-300 tokens
        chunk_overlap: int = 50,  # ~50 tokens overlap
        length_function: callable = len,
        separators: Optional[List[str]] = None
    ):
        """
        Initialize the DiaryTextSplitter.
        
        Args:
            chunk_size: Maximum chunk size in characters (~300 chars ≈ 200-300 tokens)
            chunk_overlap: Overlap between chunks to preserve context
            length_function: Function to calculate text length
            separators: List of separators for splitting (sentence-aware)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function
        
        # Diary-optimized separators (sentence and paragraph aware)
        self.separators = separators or [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentence endings
            "! ",    # Exclamation sentences
            "? ",    # Question sentences
            "; ",    # Semicolon breaks
            ", ",    # Comma breaks
            " ",     # Word breaks
            ""       # Character breaks (last resort)
        ]
        
        # Initialize recursive character splitter for long entries
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=self.length_function,
            separators=self.separators
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count from character count.
        Rule of thumb: ~4 characters per token for English text.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def _should_split_entry(self, content: str) -> bool:
        """
        Determine if a diary entry should be split into multiple chunks.
        
        Args:
            content: Diary entry content
            
        Returns:
            True if entry should be split, False otherwise
        """
        estimated_tokens = self._estimate_tokens(content)
        # Split if entry is longer than ~250 tokens (considering our 200-300 target)
        return estimated_tokens > 250
    
    def _create_chunk_metadata(self, original_doc: Document, chunk_index: int, total_chunks: int) -> Dict[str, Any]:
        """
        Create metadata for a chunk, preserving original metadata.
        
        Args:
            original_doc: Original document
            chunk_index: Index of current chunk (0-based)
            total_chunks: Total number of chunks for this entry
            
        Returns:
            Metadata dictionary for the chunk
        """
        chunk_metadata = original_doc.metadata.copy()
        
        # Add chunk-specific metadata
        chunk_metadata.update({
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "is_chunked": total_chunks > 1,
            "chunk_id": f"{chunk_metadata.get('entry_id', 'unknown')}_{chunk_index}"
        })
        
        return chunk_metadata
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split diary documents into optimized chunks.
        
        Args:
            documents: List of diary entry documents
            
        Returns:
            List of chunked documents with preserved metadata
        """
        chunked_documents = []
        
        for doc in documents:
            content = doc.page_content
            
            # Check if entry needs splitting
            if not self._should_split_entry(content):
                # Keep as single chunk for short entries
                chunk_metadata = self._create_chunk_metadata(doc, 0, 1)
                
                chunked_doc = Document(
                    page_content=content,
                    metadata=chunk_metadata
                )
                chunked_documents.append(chunked_doc)
                
                logger.debug(f"Entry {doc.metadata.get('entry_id', 'unknown')} kept as single chunk")
                
            else:
                # Split long entry into multiple chunks
                text_chunks = self.text_splitter.split_text(content)
                total_chunks = len(text_chunks)
                
                logger.info(f"Entry {doc.metadata.get('entry_id', 'unknown')} split into {total_chunks} chunks")
                
                for i, chunk_text in enumerate(text_chunks):
                    chunk_metadata = self._create_chunk_metadata(doc, i, total_chunks)
                    
                    # Add chunk position information
                    chunk_metadata["chunk_position"] = "start" if i == 0 else "end" if i == total_chunks - 1 else "middle"
                    
                    chunked_doc = Document(
                        page_content=chunk_text,
                        metadata=chunk_metadata
                    )
                    chunked_documents.append(chunked_doc)
        
        logger.info(f"Split {len(documents)} entries into {len(chunked_documents)} chunks")
        return chunked_documents
    
    def get_chunk_stats(self, documents: List[Document]) -> Dict[str, Any]:
        """
        Get statistics about chunking results.
        
        Args:
            documents: List of chunked documents
            
        Returns:
            Dictionary with chunking statistics
        """
        total_chunks = len(documents)
        single_chunks = sum(1 for doc in documents if doc.metadata.get("total_chunks", 1) == 1)
        multi_chunks = total_chunks - single_chunks
        
        unique_entries = len(set(doc.metadata.get("entry_id", "unknown") for doc in documents))
        
        avg_chunk_size = sum(len(doc.page_content) for doc in documents) / total_chunks if total_chunks > 0 else 0
        avg_tokens = sum(self._estimate_tokens(doc.page_content) for doc in documents) / total_chunks if total_chunks > 0 else 0
        
        return {
            "total_chunks": total_chunks,
            "unique_entries": unique_entries,
            "single_chunk_entries": single_chunks,
            "multi_chunk_entries": multi_chunks,
            "avg_chunk_size_chars": round(avg_chunk_size, 2),
            "avg_chunk_size_tokens": round(avg_tokens, 2),
            "chunking_ratio": round(total_chunks / unique_entries, 2) if unique_entries > 0 else 0
        }
    
    def split_diary_entry(self, entry: Dict[str, Any]) -> List[Document]:
        """
        Split a single diary entry into document chunks.
        
        Args:
            entry: Dictionary containing diary entry data
            
        Returns:
            List of Document objects
        """
        # Create Document from entry
        content = entry.get('content', '')
        
        # Extract title from content if it's in structured format
        title = ""
        actual_content = content
        
        if content.startswith("Title: "):
            lines = content.split('\n')
            for line in lines:
                if line.startswith("Title: "):
                    title = line.replace("Title: ", "").strip()
                elif line.startswith("Content: "):
                    actual_content = line.replace("Content: ", "").strip()
        
        # Create metadata
        metadata = {
            "entry_id": str(entry.get('id', 'unknown')),
            "user_id": entry.get('user_id', 1),
            "date": entry.get('date', ''),
            "tags": entry.get('tags', ''),
            "created_at": entry.get('created_at', ''),
            "type": "diary_entry",
            "content_length": len(actual_content),
            "word_count": len(actual_content.split())
        }
        
        if title:
            metadata["title"] = title
        
        # Create Document
        doc = Document(
            page_content=actual_content,
            metadata=metadata
        )
        
        # Split using the existing split_documents method
        return self.split_documents([doc])
