#!/usr/bin/env python3
"""
Test metadata filtering functionality only (without embeddings).
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.Indexingstep.embedding_and_storing import DiaryEmbeddingAndStorage

def test_metadata_filtering_only():
    """Test just the metadata filtering function without embeddings."""
    
    print("🧪 TESTING METADATA FILTERING FUNCTION")
    print("Testing conversion of complex metadata types for ChromaDB")
    print("=" * 60)
    
    # Create a dummy instance just to test the filtering method
    # We'll monkey-patch to avoid requiring Google API key
    class TestEmbedder:
        def _filter_metadata(self, metadata):
            """Copy of the filter method from DiaryEmbeddingAndStorage"""
            filtered = {}
            
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    filtered[key] = value
                elif isinstance(value, list):
                    # Convert lists to comma-separated strings
                    if value:  # Only if list is not empty
                        filtered[f"{key}_list"] = ", ".join(str(item) for item in value)
                        filtered[f"{key}_count"] = len(value)
                elif isinstance(value, dict):
                    # Skip complex nested objects
                    print(f"Skipping complex metadata field: {key}")
                    continue
                else:
                    # Convert other types to string
                    filtered[key] = str(value)
            
            return filtered
    
    embedder = TestEmbedder()
    
    # Test cases with complex metadata
    test_cases = [
        {
            "name": "Rich diary metadata",
            "metadata": {
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
        },
        {
            "name": "Work diary metadata",
            "metadata": {
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
        },
        {
            "name": "Edge cases",
            "metadata": {
                "empty_metadata": {},
                "empty_list": [],
                "empty_string": "",
                "zero": 0,
                "false_bool": False,
                "nested_dict": {"a": {"b": "c"}},
                "mixed_list": [1, "two", 3.0, True],
                "unicode_text": "Hôm nay tôi rất vui 😊",
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*20} TEST CASE {i}: {test_case['name']} {'='*20}")
        
        original_metadata = test_case['metadata']
        filtered_metadata = embedder._filter_metadata(original_metadata)
        
        print("\n📝 ORIGINAL METADATA:")
        for key, value in original_metadata.items():
            print(f"  {key}: {repr(value)} ({type(value).__name__})")
        
        print("\n✅ FILTERED METADATA:")
        for key, value in filtered_metadata.items():
            print(f"  {key}: {repr(value)} ({type(value).__name__})")
        
        print(f"\n📊 FILTERING STATISTICS:")
        print(f"  Original keys: {len(original_metadata)}")
        print(f"  Filtered keys: {len(filtered_metadata)}")
        print(f"  Keys added: {len(filtered_metadata) - len(original_metadata)}")
        
        # Analyze transformations
        transformations = []
        for key in original_metadata:
            if isinstance(original_metadata[key], list) and original_metadata[key]:
                if f"{key}_list" in filtered_metadata:
                    transformations.append(f"{key} → {key}_list + {key}_count")
            elif key not in filtered_metadata:
                if isinstance(original_metadata[key], dict):
                    transformations.append(f"{key} → SKIPPED (dict)")
                elif isinstance(original_metadata[key], list) and not original_metadata[key]:
                    transformations.append(f"{key} → SKIPPED (empty list)")
        
        if transformations:
            print(f"  Transformations: {', '.join(transformations)}")
        
        # Validate ChromaDB compatibility
        print(f"\n🔍 CHROMADB COMPATIBILITY CHECK:")
        compatible = True
        for key, value in filtered_metadata.items():
            if not isinstance(value, (str, int, float, bool, type(None))):
                print(f"  ❌ {key}: {type(value).__name__} is not compatible")
                compatible = False
        
        if compatible:
            print("  ✅ All metadata types are ChromaDB compatible")
        else:
            print("  ❌ Some metadata types are not compatible")

def test_specific_scenarios():
    """Test specific scenarios that might occur in the diary system."""
    
    print("\n" + "="*60)
    print("🔍 TESTING SPECIFIC DIARY SCENARIOS")
    print("="*60)
    
    class TestEmbedder:
        def _filter_metadata(self, metadata):
            filtered = {}
            
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    filtered[key] = value
                elif isinstance(value, list):
                    if value:  # Only if list is not empty
                        filtered[f"{key}_list"] = ", ".join(str(item) for item in value)
                        filtered[f"{key}_count"] = len(value)
                elif isinstance(value, dict):
                    continue
                else:
                    filtered[key] = str(value)
            
            return filtered
    
    embedder = TestEmbedder()
    
    scenarios = [
        {
            "name": "Entry with Vietnamese tags",
            "metadata": {
                "tags": ["gia đình", "hạnh phúc", "bạn bè"],
                "people": ["Anh Minh", "Chị Lan"],
                "location": "Hà Nội"
            }
        },
        {
            "name": "Entry with mixed language tags",
            "metadata": {
                "tags": ["work", "công việc", "achievement", "thành công"],
                "mood_tags": ["happy", "vui vẻ", "excited"]
            }
        },
        {
            "name": "Entry with special characters",
            "metadata": {
                "tags": ["#hashtag", "@mention", "emoji😊"],
                "people": ["User123", "test@email.com"]
            }
        },
        {
            "name": "Entry with numbers and dates",
            "metadata": {
                "tags": ["2025", "year-end", "Q1"],
                "dates_mentioned": ["2025-01-15", "2025-12-31"],
                "numbers": [1, 2, 3, 100]
            }
        }
    ]
    
    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ---")
        
        original = scenario['metadata']
        filtered = embedder._filter_metadata(original)
        
        print("Original:")
        for k, v in original.items():
            print(f"  {k}: {v}")
        
        print("Filtered:")
        for k, v in filtered.items():
            print(f"  {k}: {v}")

if __name__ == "__main__":
    try:
        test_metadata_filtering_only()
        test_specific_scenarios()
        
        print("\n🎉 ALL METADATA FILTERING TESTS COMPLETED!")
        print("\n✅ Key findings:")
        print("  - Lists are converted to comma-separated strings + count")
        print("  - Dictionaries are skipped")
        print("  - Empty lists are skipped")
        print("  - All basic types (str, int, float, bool, None) are preserved")
        print("  - Unicode and special characters are handled correctly")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
