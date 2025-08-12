"""
Test script for enhanced diary indexing with optimized metadata and chunking.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src', 'Indexingstep'))

from src.Indexingstep.dataloading import DiaryDataLoader
from src.Indexingstep.diary_text_splitter import DiaryTextSplitter
from src.Indexingstep.pipeline import DiaryIndexingPipeline
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_enhanced_data_loading():
    """Test enhanced data loading with rich metadata."""
    print("\n" + "="*50)
    print("TESTING ENHANCED DATA LOADING")
    print("="*50)
    
    # Initialize data loader
    db_path = "./src/streamlit_app/backend/diary.db"
    loader = DiaryDataLoader(
        db_path=db_path,
        table_name="diary_entries",
        content_column="content",
        date_column="date",
        tags_column="tags",
        id_column="id"
    )
    
    # Load documents
    documents = loader.load()
    
    print(f"Loaded {len(documents)} diary entries")
    
    # Show metadata for first few entries
    for i, doc in enumerate(documents[:3]):
        print(f"\n--- Entry {i+1} ---")
        print(f"Content preview: {doc.page_content[:100]}...")
        print("Metadata:")
        for key, value in doc.metadata.items():
            print(f"  {key}: {value}")
    
    return documents

def test_diary_text_splitter(documents):
    """Test diary-specific text splitter."""
    print("\n" + "="*50)
    print("TESTING DIARY TEXT SPLITTER")
    print("="*50)
    
    # Initialize splitter
    splitter = DiaryTextSplitter(
        chunk_size=300,
        chunk_overlap=50
    )
    
    # Split documents
    split_docs = splitter.split_documents(documents)
    
    # Get statistics
    stats = splitter.get_chunk_stats(split_docs)
    
    print("Chunking Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Show examples of chunks
    print(f"\nExamples of chunks:")
    for i, doc in enumerate(split_docs[:5]):
        print(f"\n--- Chunk {i+1} ---")
        print(f"Content: {doc.page_content[:150]}...")
        print(f"Entry ID: {doc.metadata.get('entry_id', 'N/A')}")
        print(f"Chunk {doc.metadata.get('chunk_index', 0)+1}/{doc.metadata.get('total_chunks', 1)}")
        print(f"Tags: {doc.metadata.get('tags', [])}")
        print(f"Day of week: {doc.metadata.get('day_of_week', 'N/A')}")
        if doc.metadata.get('location'):
            print(f"Location: {doc.metadata.get('location')}")
        if doc.metadata.get('people'):
            print(f"People: {doc.metadata.get('people')}")
    
    return split_docs

def test_enhanced_pipeline():
    """Test the complete enhanced pipeline."""
    print("\n" + "="*50)
    print("TESTING ENHANCED INDEXING PIPELINE")
    print("="*50)
    
    # Load environment
    load_dotenv("./src/Indexingstep/.env")
    
    config = {
        "google_api_key": os.getenv("GOOGLE_API_KEY"),
        "db_path": "./src/streamlit_app/backend/diary.db",
        "persist_directory": "./src/Indexingstep/diary_vector_db_enhanced",
        "collection_name": "enhanced_diary_entries",
        "embedding_model": "models/embedding-001",
        "chunk_size": 300,  # Optimized for diary entries
        "chunk_overlap": 50,  # 50-token sliding window
        "batch_size": 50
    }
    
    if not config["google_api_key"]:
        print("❌ Google API key not found. Skipping full pipeline test.")
        return
    
    try:
        # Initialize pipeline
        pipeline = DiaryIndexingPipeline(
            db_path=config["db_path"],
            persist_directory=config["persist_directory"],
            collection_name=config["collection_name"],
            google_api_key=config["google_api_key"],
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
            embedding_model=config["embedding_model"],
            batch_size=config["batch_size"]
        )
        
        # Run full indexing
        print("Starting enhanced indexing...")
        results = pipeline.run_full_pipeline()
        
        print("Enhanced Indexing Results:")
        for key, value in results.items():
            print(f"  {key}: {value}")
        
        # Test search with enhanced metadata
        test_enhanced_search(pipeline)
        
    except Exception as e:
        logger.error(f"Error in enhanced pipeline test: {e}")

def test_enhanced_search(pipeline):
    """Test search functionality with enhanced metadata."""
    print("\n" + "-"*30)
    print("TESTING ENHANCED SEARCH")
    print("-"*30)
    
    test_queries = [
        "work project achievement",
        "family dinner happiness",
        "learning programming technology",
        "travel mountain adventure"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        try:
            results = pipeline.embedding_storage.similarity_search(
                query=query,
                k=3
            )
            
            for i, result in enumerate(results[:2]):  # Show top 2 results
                print(f"  Result {i+1}:")
                print(f"    Content: {result.page_content[:100]}...")
                print(f"    Date: {result.metadata.get('date', 'N/A')}")
                print(f"    Day: {result.metadata.get('day_of_week', 'N/A')}")
                print(f"    Tags: {result.metadata.get('tags', [])}")
                if result.metadata.get('location'):
                    print(f"    Location: {result.metadata.get('location')}")
                if result.metadata.get('mood_tags'):
                    print(f"    Mood: {result.metadata.get('mood_tags')}")
                
        except Exception as e:
            print(f"    Error: {e}")

def main():
    """Main test function."""
    print("🧪 ENHANCED DIARY INDEXING TESTS")
    print("Testing optimized indexing with rich metadata and smart chunking")
    
    try:
        # Test 1: Enhanced data loading
        documents = test_enhanced_data_loading()
        
        # Test 2: Diary text splitter
        split_docs = test_diary_text_splitter(documents)
        
        # Test 3: Enhanced pipeline
        test_enhanced_pipeline()
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()
