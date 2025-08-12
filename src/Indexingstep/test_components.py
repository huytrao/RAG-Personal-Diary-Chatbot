#!/usr/bin/env python
"""
Test script for the diary indexing components.
This script tests individual components before running the full pipeline.
"""

import os
import sys
import tempfile
import sqlite3
from typing import List

# Add the parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataloading import DiaryDataLoader, DiaryContentPreprocessor
from Datasplitting import DataSplitting
from embedding_and_storing import DiaryEmbeddingAndStorage
from langchain.schema import Document
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_database():
    """Create a temporary test database with sample diary entries."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    # Connect and create table
    conn = sqlite3.connect(temp_db.name)
    cursor = conn.cursor()
    
    # Create diary_entries table
    cursor.execute('''
        CREATE TABLE diary_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            date TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert sample data
    sample_entries = [
        ("Today was a wonderful day! I went to the park with my family and we had a great picnic. The weather was perfect and the kids enjoyed playing on the swings. I felt so grateful for these precious moments.", "2024-01-15"),
        ("Had a challenging day at work today. The project deadline is approaching and there's still a lot to be done. However, I learned some new programming techniques that will be useful in the future. Feeling determined to push through.", "2024-01-16"),
        ("Spent the evening reading a fascinating book about artificial intelligence. The concepts are complex but incredibly interesting. I'm amazed by how technology is advancing. Made some notes for future reference.", "2024-01-17"),
        ("Feeling a bit under the weather today. Decided to stay home and rest. Watched some movies and drank lots of tea. Sometimes it's important to take care of yourself and not push too hard.", "2024-01-18"),
        ("Visited my grandmother today. She told me wonderful stories about her childhood. Her wisdom and life experiences always inspire me. We cooked her famous apple pie together - such a special memory.", "2024-01-19")
    ]
    
    cursor.executemany(
        "INSERT INTO diary_entries (content, date) VALUES (?, ?)",
        sample_entries
    )
    
    conn.commit()
    conn.close()
    
    logger.info(f"Created test database: {temp_db.name}")
    return temp_db.name

def test_data_loading(db_path: str):
    """Test the data loading component."""
    print("\n" + "="*50)
    print("TESTING DATA LOADING")
    print("="*50)
    
    try:
        # Initialize loader
        loader = DiaryDataLoader(
            db_path=db_path,
            table_name="diary_entries",
            content_column="content",
            date_column="date"
        )
        
        # Test loading all documents
        documents = loader.load()
        print(f"✓ Loaded {len(documents)} documents")
        
        # Test date range loading
        filtered_docs = loader.load_by_date_range("2024-01-16", "2024-01-18")
        print(f"✓ Loaded {len(filtered_docs)} documents in date range")
        
        # Test table info
        table_info = loader.get_table_info()
        print(f"✓ Table info: {table_info['row_count']} rows")
        
        # Show sample document
        if documents:
            sample_doc = documents[0]
            print(f"✓ Sample document content: {sample_doc.page_content[:100]}...")
            print(f"✓ Sample document metadata: {sample_doc.metadata}")
        
        return True, documents
        
    except Exception as e:
        print(f"✗ Data loading failed: {str(e)}")
        return False, []

def test_preprocessing(documents: List[Document]):
    """Test the preprocessing component."""
    print("\n" + "="*50)
    print("TESTING PREPROCESSING")
    print("="*50)
    
    try:
        # Initialize preprocessor
        preprocessor = DiaryContentPreprocessor(
            remove_extra_whitespace=True,
            normalize_line_breaks=True,
            min_content_length=10,
            max_content_length=1000
        )
        
        # Test preprocessing
        preprocessed_docs = preprocessor.preprocess_documents(documents)
        print(f"✓ Preprocessed {len(documents)} → {len(preprocessed_docs)} documents")
        
        # Test individual content preprocessing
        test_content = "This   has    extra   spaces\n\n\nand\r\nmultiple\nline\nbreaks"
        processed_content = preprocessor.preprocess_content(test_content)
        print(f"✓ Content preprocessing: '{test_content}' → '{processed_content}'")
        
        return True, preprocessed_docs
        
    except Exception as e:
        print(f"✗ Preprocessing failed: {str(e)}")
        return False, []

def test_splitting(documents: List[Document]):
    """Test the document splitting component."""
    print("\n" + "="*50)
    print("TESTING DOCUMENT SPLITTING")
    print("="*50)
    
    try:
        # Initialize splitter
        splitter = DataSplitting(
            chunk_size=200,
            chunk_overlap=50,
            separator="\n\n"
        )
        
        # Test splitting
        split_docs = splitter.split_documents(documents)
        print(f"✓ Split {len(documents)} documents into {len(split_docs)} chunks")
        
        # Test text splitting
        test_text = "This is a long text. " * 50  # Create long text
        chunks = splitter.split_text(test_text)
        print(f"✓ Split test text into {len(chunks)} chunks")
        
        # Show sample chunk
        if split_docs:
            sample_chunk = split_docs[0]
            print(f"✓ Sample chunk: {sample_chunk.page_content[:100]}...")
        
        return True, split_docs
        
    except Exception as e:
        print(f"✗ Document splitting failed: {str(e)}")
        return False, []

def test_embedding_and_storage(documents: List[Document], test_with_api: bool = False):
    """Test the embedding and storage component."""
    print("\n" + "="*50)
    print("TESTING EMBEDDING AND STORAGE")
    print("="*50)
    
    if not test_with_api:
        print("⚠ Skipping embedding test (no API key provided)")
        print("  To test embeddings, set GOOGLE_API_KEY environment variable")
        return True, []
    
    try:
        # Create temporary vector database
        temp_dir = tempfile.mkdtemp()
        
        # Initialize embedding storage
        embedding_storage = DiaryEmbeddingAndStorage(
            api_key=os.getenv("GOOGLE_API_KEY"),
            persist_directory=temp_dir,
            collection_name="test_collection"
        )
        
        # Test embedding and storage
        doc_ids = embedding_storage.embed_and_store_documents(documents[:2])  # Test with first 2 docs
        print(f"✓ Embedded and stored {len(doc_ids)} documents")
        
        # Test similarity search
        search_results = embedding_storage.similarity_search("happy day", k=2)
        print(f"✓ Similarity search returned {len(search_results)} results")
        
        # Test collection info
        info = embedding_storage.get_collection_info()
        print(f"✓ Collection info: {info}")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        
        return True, doc_ids
        
    except Exception as e:
        print(f"✗ Embedding and storage failed: {str(e)}")
        return False, []

def run_all_tests():
    """Run all component tests."""
    print("="*70)
    print("DIARY INDEXING COMPONENT TESTS")
    print("="*70)
    
    # Create test database
    db_path = create_test_database()
    
    try:
        # Test 1: Data Loading
        success1, documents = test_data_loading(db_path)
        
        if not success1 or not documents:
            print("\n✗ Cannot continue tests without valid documents")
            return False
        
        # Test 2: Preprocessing
        success2, preprocessed_docs = test_preprocessing(documents)
        
        if not success2 or not preprocessed_docs:
            print("\n✗ Cannot continue tests without preprocessed documents")
            return False
        
        # Test 3: Document Splitting
        success3, split_docs = test_splitting(preprocessed_docs)
        
        if not success3:
            print("\n✗ Document splitting failed")
            return False
        
        # Test 4: Embedding and Storage (optional, requires API key)
        has_api_key = bool(os.getenv("GOOGLE_API_KEY"))
        success4, _ = test_embedding_and_storage(split_docs[:2], test_with_api=has_api_key)
        
        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Data Loading: {'✓ PASSED' if success1 else '✗ FAILED'}")
        print(f"Preprocessing: {'✓ PASSED' if success2 else '✗ FAILED'}")
        print(f"Document Splitting: {'✓ PASSED' if success3 else '✗ FAILED'}")
        
        if has_api_key:
            print(f"Embedding & Storage: {'✓ PASSED' if success4 else '✗ FAILED'}")
        else:
            print("Embedding & Storage: ⚠ SKIPPED (no API key)")
        
        overall_success = success1 and success2 and success3 and (success4 if has_api_key else True)
        print(f"\nOverall: {'✓ ALL TESTS PASSED' if overall_success else '✗ SOME TESTS FAILED'}")
        
        return overall_success
        
    finally:
        # Cleanup test database
        try:
            os.unlink(db_path)
            logger.info(f"Cleaned up test database: {db_path}")
        except:
            pass

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test diary indexing components")
    parser.add_argument(
        "--with-embeddings",
        action="store_true",
        help="Test embeddings (requires GOOGLE_API_KEY)"
    )
    
    args = parser.parse_args()
    
    if args.with_embeddings and not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY environment variable required for embedding tests")
        return False
    
    # Run tests
    success = run_all_tests()
    
    if success:
        print("\n🎉 All tests completed successfully!")
        print("The indexing pipeline components are ready to use.")
    else:
        print("\n❌ Some tests failed.")
        print("Please check the error messages and fix issues before proceeding.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
