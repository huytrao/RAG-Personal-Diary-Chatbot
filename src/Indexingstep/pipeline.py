import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataloading import DiaryDataLoader, DiaryContentPreprocessor
from diary_text_splitter import DiaryTextSplitter
from embedding_and_storing import DiaryEmbeddingAndStorage
from langchain.schema import Document
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DiaryIndexingPipeline:
    """
    Enhanced pipeline for indexing diary entries with optimized chunking and metadata.
    Integrates data loading, preprocessing, diary-specific splitting, embedding, and storage.
    """
    
    def __init__(
        self,
        db_path: str = "./diary.db",
        persist_directory: str = "./chroma_db",
        collection_name: str = "diary_collection",
        google_api_key: Optional[str] = None,
        chunk_size: int = 300,  # Optimized for diary entries (200-300 tokens)
        chunk_overlap: int = 50,  # 50-token sliding window
        embedding_model: str = "models/embedding-001",
        batch_size: int = 50
    ):
        """
        Initialize the enhanced diary indexing pipeline.
        
        Args:
            db_path (str): Path to SQLite database
            persist_directory (str): Directory for vector database
            collection_name (str): Name of the collection
            google_api_key (str, optional): Google API key for embeddings
            chunk_size (int): Size of text chunks (optimized for diary entries)
            chunk_overlap (int): Overlap between chunks (sliding window)
            embedding_model (str): Google embedding model name
            batch_size (int): Batch size for processing
        """
        self.db_path = db_path
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.batch_size = batch_size
        
        # Validate database exists
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found: {db_path}")
        
        # Initialize components
        self._initialize_components(
            google_api_key, chunk_size, chunk_overlap, embedding_model
        )
        
        logger.info("Diary Indexing Pipeline initialized successfully")
    
    def _initialize_components(
        self, 
        google_api_key: Optional[str], 
        chunk_size: int, 
        chunk_overlap: int,
        embedding_model: str
    ):
        """Initialize all pipeline components."""
        
        # 1. Data Loader
        self.data_loader = DiaryDataLoader(
            db_path=self.db_path,
            table_name="diary_entries",
            content_column="content",
            date_column="date"
        )
        
        # 2. Content Preprocessor
        self.preprocessor = DiaryContentPreprocessor(
            remove_extra_whitespace=True,
            normalize_line_breaks=True,
            min_content_length=3,  # Keep short entries
            max_content_length=10000
        )
        
        # 3. Diary-optimized Text Splitter
        self.text_splitter = DiaryTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # 4. Embedding and Storage
        self.embedding_storage = DiaryEmbeddingAndStorage(
            api_key=google_api_key,
            persist_directory=self.persist_directory,
            collection_name=self.collection_name,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        logger.info("All pipeline components initialized")
    
    def load_diary_data(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Document]:
        """
        Load diary entries from database.
        
        Args:
            start_date (str, optional): Start date filter (YYYY-MM-DD)
            end_date (str, optional): End date filter (YYYY-MM-DD)
            
        Returns:
            List[Document]: Loaded diary documents
        """
        try:
            logger.info("Loading diary entries from database...")
            
            if start_date and end_date:
                documents = self.data_loader.load_by_date_range(start_date, end_date)
                logger.info(f"Loaded {len(documents)} entries from {start_date} to {end_date}")
            else:
                documents = self.data_loader.load()
                logger.info(f"Loaded {len(documents)} total diary entries")
            
            if not documents:
                logger.warning("No diary entries found in database")
                return []
            
            return documents
            
        except Exception as e:
            logger.error(f"Error loading diary data: {str(e)}")
            raise
    
    def preprocess_documents(self, documents: List[Document]) -> List[Document]:
        """
        Preprocess diary documents.
        
        Args:
            documents (List[Document]): Raw documents
            
        Returns:
            List[Document]: Preprocessed documents
        """
        try:
            logger.info(f"Preprocessing {len(documents)} documents...")
            
            preprocessed_docs = self.preprocessor.preprocess_documents(documents)
            
            logger.info(f"Preprocessing complete: {len(preprocessed_docs)} documents kept")
            return preprocessed_docs
            
        except Exception as e:
            logger.error(f"Error preprocessing documents: {str(e)}")
            raise
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into optimized chunks using diary-specific splitter.
        
        Args:
            documents (List[Document]): Documents to split
            
        Returns:
            List[Document]: Split document chunks with enhanced metadata
        """
        try:
            logger.info(f"Splitting {len(documents)} diary entries into optimized chunks...")
            
            split_docs = self.text_splitter.split_documents(documents)
            
            # Get and log chunking statistics
            stats = self.text_splitter.get_chunk_stats(split_docs)
            logger.info(f"Document splitting complete: {stats}")
            
            return split_docs
            
        except Exception as e:
            logger.error(f"Error splitting documents: {str(e)}")
            raise
    
    def embed_and_store(self, documents: List[Document]) -> List[str]:
        """
        Generate embeddings and store documents.
        
        Args:
            documents (List[Document]): Documents to embed and store
            
        Returns:
            List[str]: Document IDs
        """
        try:
            logger.info(f"Generating embeddings and storing {len(documents)} document chunks...")
            
            # Process in batches for large datasets
            if len(documents) > self.batch_size:
                document_ids = self.embedding_storage.batch_process_documents(
                    documents, self.batch_size
                )
            else:
                document_ids = self.embedding_storage.embed_and_store_documents(documents)
            
            logger.info(f"Successfully embedded and stored {len(document_ids)} documents")
            return document_ids
            
        except Exception as e:
            logger.error(f"Error embedding and storing documents: {str(e)}")
            raise
    
    def run_full_pipeline(
        self, 
        start_date: Optional[str] = None, 
        end_date: Optional[str] = None,
        clear_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete indexing pipeline.
        
        Args:
            start_date (str, optional): Start date filter
            end_date (str, optional): End date filter
            clear_existing (bool): Whether to clear existing data
            
        Returns:
            Dict: Pipeline execution results
        """
        try:
            logger.info("="*60)
            logger.info("STARTING DIARY INDEXING PIPELINE")
            logger.info("="*60)
            
            pipeline_stats = {
                "status": "running",
                "steps_completed": 0,
                "total_steps": 5,
                "documents_loaded": 0,
                "documents_preprocessed": 0,
                "chunks_created": 0,
                "documents_stored": 0,
                "errors": []
            }
            
            # Step 1: Clear existing data if requested
            if clear_existing:
                logger.info("Step 1: Clearing existing vector store...")
                self.embedding_storage.clear_collection()
                pipeline_stats["steps_completed"] += 1
            
            # Step 2: Load diary data
            logger.info("Step 2: Loading diary entries...")
            documents = self.load_diary_data(start_date, end_date)
            pipeline_stats["documents_loaded"] = len(documents)
            pipeline_stats["steps_completed"] += 1
            
            if not documents:
                pipeline_stats["status"] = "completed_with_warnings"
                pipeline_stats["errors"].append("No documents found to process")
                return pipeline_stats
            
            # Step 3: Preprocess documents
            logger.info("Step 3: Preprocessing documents...")
            preprocessed_docs = self.preprocess_documents(documents)
            pipeline_stats["documents_preprocessed"] = len(preprocessed_docs)
            pipeline_stats["steps_completed"] += 1
            
            if not preprocessed_docs:
                pipeline_stats["status"] = "failed"
                pipeline_stats["errors"].append("No documents survived preprocessing")
                return pipeline_stats
            
            # Step 4: Split documents into chunks
            logger.info("Step 4: Splitting documents into chunks...")
            split_docs = self.split_documents(preprocessed_docs)
            pipeline_stats["chunks_created"] = len(split_docs)
            pipeline_stats["steps_completed"] += 1
            
            # Step 5: Generate embeddings and store
            logger.info("Step 5: Generating embeddings and storing...")
            document_ids = self.embed_and_store(split_docs)
            pipeline_stats["documents_stored"] = len(document_ids)
            pipeline_stats["steps_completed"] += 1
            
            # Update final status
            pipeline_stats["status"] = "completed_successfully"
            
            logger.info("="*60)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY!")
            logger.info("="*60)
            logger.info(f"Documents loaded: {pipeline_stats['documents_loaded']}")
            logger.info(f"Documents preprocessed: {pipeline_stats['documents_preprocessed']}")
            logger.info(f"Chunks created: {pipeline_stats['chunks_created']}")
            logger.info(f"Documents stored: {pipeline_stats['documents_stored']}")
            logger.info("="*60)
            
            return pipeline_stats
            
        except Exception as e:
            logger.error(f"Pipeline failed with error: {str(e)}")
            pipeline_stats["status"] = "failed"
            pipeline_stats["errors"].append(str(e))
            return pipeline_stats
    
    def incremental_update(self, start_date: str, end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Perform incremental update for new diary entries.
        
        Args:
            start_date (str): Start date for incremental update
            end_date (str, optional): End date for incremental update
            
        Returns:
            Dict: Update results
        """
        try:
            logger.info(f"Starting incremental update from {start_date}")
            
            # Load only new entries
            new_documents = self.load_diary_data(start_date, end_date)
            
            if not new_documents:
                logger.info("No new documents found for incremental update")
                return {"status": "no_updates", "documents_added": 0}
            
            # Process new documents
            preprocessed_docs = self.preprocess_documents(new_documents)
            split_docs = self.split_documents(preprocessed_docs)
            document_ids = self.embed_and_store(split_docs)
            
            logger.info(f"Incremental update completed: {len(document_ids)} new documents added")
            
            return {
                "status": "success",
                "documents_loaded": len(new_documents),
                "documents_added": len(document_ids)
            }
            
        except Exception as e:
            logger.error(f"Incremental update failed: {str(e)}")
            return {"status": "failed", "error": str(e)}
    
    def search_similar_entries(
        self, 
        query: str, 
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Search for similar diary entries.
        
        Args:
            query (str): Search query
            k (int): Number of results to return
            filter_metadata (Dict, optional): Metadata filter
            
        Returns:
            List[Document]: Similar documents
        """
        try:
            return self.embedding_storage.similarity_search(
                query=query,
                k=k,
                filter=filter_metadata
            )
        except Exception as e:
            logger.error(f"Error searching similar entries: {str(e)}")
            return []
    
    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive pipeline statistics.
        
        Returns:
            Dict: Pipeline and database statistics
        """
        try:
            # Database stats
            db_info = self.data_loader.get_table_info()
            
            # Vector store stats
            vector_info = self.embedding_storage.get_collection_info()
            
            return {
                "database": db_info,
                "vector_store": vector_info,
                "pipeline_config": {
                    "chunk_size": self.text_splitter.chunk_size,
                    "chunk_overlap": self.text_splitter.chunk_overlap,
                    "batch_size": self.batch_size,
                    "collection_name": self.collection_name
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting pipeline stats: {str(e)}")
            return {}

def main():
    """Main function to demonstrate pipeline usage."""
    
    # Configuration
    config = {
        "db_path": "../streamlit_app/diary.db",  # Adjust path as needed
        "persist_directory": "./diary_vector_db",
        "collection_name": "diary_entries",
        "google_api_key": None,  # Set your API key or use environment variable
        "chunk_size": 800,
        "chunk_overlap": 100,
        "batch_size": 50
    }
    
    try:
        # Initialize pipeline
        logger.info("Initializing Diary Indexing Pipeline...")
        pipeline = DiaryIndexingPipeline(**config)
        
        # Run full pipeline
        results = pipeline.run_full_pipeline(clear_existing=True)
        
        # Print results
        print("\n" + "="*60)
        print("PIPELINE EXECUTION RESULTS")
        print("="*60)
        print(f"Status: {results['status']}")
        print(f"Steps completed: {results['steps_completed']}/{results['total_steps']}")
        print(f"Documents loaded: {results['documents_loaded']}")
        print(f"Documents preprocessed: {results['documents_preprocessed']}")
        print(f"Chunks created: {results['chunks_created']}")
        print(f"Documents stored: {results['documents_stored']}")
        
        if results['errors']:
            print(f"Errors: {results['errors']}")
        
        # Get and display stats
        stats = pipeline.get_pipeline_stats()
        print("\nPIPELINE STATISTICS:")
        print(f"Database entries: {stats.get('database', {}).get('row_count', 'N/A')}")
        print(f"Vector store documents: {stats.get('vector_store', {}).get('document_count', 'N/A')}")
        print("="*60)
        
        # Example search
        if results['status'] == 'completed_successfully':
            print("\nTesting similarity search...")
            search_results = pipeline.search_similar_entries("happy day", k=3)
            print(f"Found {len(search_results)} similar entries")
            for i, doc in enumerate(search_results[:2]):
                print(f"Result {i+1}: {doc.page_content[:100]}...")
        
    except Exception as e:
        logger.error(f"Main execution failed: {str(e)}")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()