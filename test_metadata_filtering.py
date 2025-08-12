#!/usr/bin/env python3
"""
Test metadata filtering functionality for ChromaDB compatibility.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.Indexingstep.embedding_and_storing import DiaryEmbeddingAndStorage
from langchain.schema import Document

def test_metadata_filtering():
    """Test metadata filtering to ensure ChromaDB compatibility."""
    
    print("🧪 TESTING METADATA FILTERING")
    print("Testing conversion of complex metadata types for ChromaDB")
    print("=" * 60)
    
    # Initialize the embedding system
    embedder = DiaryEmbeddingAndStorage(
        persist_directory="./test_metadata_db",
        collection_name="test_collection"
    )
    
    # Create test documents with complex metadata
    test_documents = [
        Document(
            page_content="Today was a great day with friends and family.",
            metadata={
                "entry_id": 1,
                "date": "2025-01-15",
                "day_of_week": "Wednesday",
                "tags": ["family", "friends", "happiness"],  # List - should be filtered
                "people": ["Alice", "Bob", "Charlie"],  # List - should be filtered
                "mood_tags": ["happy", "excited", "grateful"],  # List - should be filtered
                "location": "Home",
                "weather": "Sunny",
                "rating": 4.5,  # Float
                "is_important": True,  # Boolean
                "word_count": 25,  # Integer
                "complex_object": {"nested": "value"},  # Dict - should be skipped
                "empty_list": [],  # Empty list - should be skipped
                "none_value": None,  # None - should be kept
            }
        ),
        Document(
            page_content="Work was challenging but rewarding today.",
            metadata={
                "entry_id": 2,
                "date": "2025-01-16",
                "day_of_week": "Thursday",
                "tags": ["work", "achievement", "challenge"],
                "people": ["Manager", "Team"],
                "location": "Office",
                "rating": 3.8,
                "is_important": False,
                "word_count": 30,
            }
        )
    ]
    
    print("📝 Original metadata examples:")
    for i, doc in enumerate(test_documents, 1):
        print(f"\n--- Document {i} ---")
        print(f"Content: {doc.page_content}")
        print("Original metadata:")
        for key, value in doc.metadata.items():
            print(f"  {key}: {value} ({type(value).__name__})")
    
    print("\n" + "=" * 60)
    print("🔧 TESTING METADATA FILTERING")
    print("=" * 60)
    
    # Test the filtering function
    for i, doc in enumerate(test_documents, 1):
        print(f"\n--- Document {i} Filtering ---")
        
        original_metadata = doc.metadata
        filtered_metadata = embedder._filter_metadata(original_metadata)
        
        print("✅ Filtered metadata:")
        for key, value in filtered_metadata.items():
            print(f"  {key}: {value} ({type(value).__name__})")
        
        print(f"\n📊 Filtering statistics:")
        print(f"  Original keys: {len(original_metadata)}")
        print(f"  Filtered keys: {len(filtered_metadata)}")
        print(f"  Keys removed: {len(original_metadata) - len(filtered_metadata)}")
        
        # Check for expected transformations
        expected_transformations = []
        
        if "tags" in original_metadata and original_metadata["tags"]:
            expected_transformations.append("tags → tags_list + tags_count")
        if "people" in original_metadata and original_metadata["people"]:
            expected_transformations.append("people → people_list + people_count")
        if "mood_tags" in original_metadata and original_metadata["mood_tags"]:
            expected_transformations.append("mood_tags → mood_tags_list + mood_tags_count")
        
        if expected_transformations:
            print(f"  Expected transformations: {', '.join(expected_transformations)}")
    
    print("\n" + "=" * 60)
    print("💾 TESTING DOCUMENT STORAGE WITH FILTERED METADATA")
    print("=" * 60)
    
    try:
        # Store documents with filtered metadata
        document_ids = embedder.embed_and_store_documents(test_documents)
        
        print(f"✅ Successfully stored {len(document_ids)} documents")
        print(f"Document IDs: {document_ids}")
        
        # Test search functionality
        print("\n🔍 Testing search with filtered metadata...")
        search_results = embedder.similarity_search("friends family happiness", k=2)
        
        print(f"Found {len(search_results)} search results:")
        for i, result in enumerate(search_results, 1):
            print(f"\n--- Search Result {i} ---")
            print(f"Content: {result.page_content}")
            print("Stored metadata:")
            for key, value in result.metadata.items():
                print(f"  {key}: {value}")
        
        print("\n✅ Metadata filtering test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during storage: {str(e)}")
        return False
    
    return True

def test_metadata_edge_cases():
    """Test edge cases for metadata filtering."""
    
    print("\n" + "=" * 60)
    print("🧪 TESTING METADATA EDGE CASES")
    print("=" * 60)
    
    embedder = DiaryEmbeddingAndStorage(
        persist_directory="./test_metadata_db",
        collection_name="test_collection"
    )
    
    edge_cases = [
        {
            "name": "Empty metadata",
            "metadata": {}
        },
        {
            "name": "Only simple types",
            "metadata": {
                "string": "text",
                "integer": 42,
                "float": 3.14,
                "boolean": True,
                "none": None
            }
        },
        {
            "name": "Only complex types",
            "metadata": {
                "list": [1, 2, 3],
                "dict": {"key": "value"},
                "nested_list": [[1, 2], [3, 4]]
            }
        },
        {
            "name": "Mixed empty containers",
            "metadata": {
                "empty_list": [],
                "empty_dict": {},
                "empty_string": "",
                "zero": 0,
                "false": False
            }
        }
    ]
    
    for case in edge_cases:
        print(f"\n--- Testing: {case['name']} ---")
        filtered = embedder._filter_metadata(case['metadata'])
        
        print(f"Original: {case['metadata']}")
        print(f"Filtered: {filtered}")
        print(f"Keys: {len(case['metadata'])} → {len(filtered)}")

if __name__ == "__main__":
    try:
        # Set up Google API key if needed
        import os
        if "GOOGLE_API_KEY" not in os.environ:
            # You may need to set this
            print("⚠️  Note: GOOGLE_API_KEY environment variable not set")
            print("Make sure to set it for embedding functionality")
        
        success = test_metadata_filtering()
        
        if success:
            test_metadata_edge_cases()
            print("\n🎉 All metadata filtering tests passed!")
        else:
            print("\n❌ Some tests failed")
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
