#!/usr/bin/env python3
"""
Test script for Diary RAG System
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.Retrivel_And_Generation.Retrieval_And_Generator import DiaryRAGSystem, create_rag_system

def test_rag_system():
    """Test the RAG system functionality."""
    
    print("🧪 TESTING DIARY RAG SYSTEM")
    print("=" * 50)
    
    try:
        # Initialize RAG system
        print("\n1️⃣ Initializing RAG System...")
        rag = create_rag_system(
            vector_db_path="./src/Indexingstep/diary_vector_db_enhanced"
        )
        
        # Health check
        print("\n2️⃣ Health Check...")
        status = rag.health_check()
        print("System Status:")
        for key, value in status.items():
            print(f"  ✅ {key}: {value}")
        
        if not status.get("vector_store_healthy"):
            print("\n⚠️ Vector store not healthy. Please run indexing first.")
            return
        
        # Test basic queries
        print("\n3️⃣ Testing Basic Queries...")
        test_queries = [
            "Tôi cảm thấy như thế nào hôm nay?",
            "Có gì đặc biệt trong nhật ký của tôi không?",
            "Tâm trạng của tôi thế nào?",
            "Tôi đã làm gì trong thời gian gần đây?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Test Query {i} ---")
            print(f"❓ Query: {query}")
            
            try:
                response = rag.generate_response(query)
                print(f"🤖 Response: {response}")
                print("✅ Success")
            except Exception as e:
                print(f"❌ Error: {str(e)}")
        
        # Test retrieval only
        print("\n4️⃣ Testing Document Retrieval...")
        try:
            docs = rag.retrieve_relevant_entries("cảm xúc tâm trạng", k=3)
            print(f"📄 Retrieved {len(docs)} documents")
            
            for i, doc in enumerate(docs, 1):
                print(f"\nDocument {i}:")
                print(f"  Content: {doc.page_content[:100]}...")
                print(f"  Metadata: {doc.metadata}")
        except Exception as e:
            print(f"❌ Retrieval error: {str(e)}")
        
        # Test tag-based search
        print("\n5️⃣ Testing Tag-based Search...")
        try:
            tag_docs = rag.search_by_tags(["work", "family", "health"], k=3)
            print(f"🏷️ Found {len(tag_docs)} documents with specified tags")
            
            for i, doc in enumerate(tag_docs, 1):
                tags = doc.metadata.get('tags_list', 'No tags')
                print(f"  Doc {i}: Tags = {tags}")
        except Exception as e:
            print(f"❌ Tag search error: {str(e)}")
        
        # Test summary generation
        print("\n6️⃣ Testing Summary Generation...")
        try:
            summary = rag.generate_summary()
            print(f"📊 Summary: {summary}")
        except Exception as e:
            print(f"❌ Summary error: {str(e)}")
        
        # Test conversation context
        print("\n7️⃣ Testing Conversation Context...")
        try:
            chat_history = [
                {"role": "user", "content": "Tôi cảm thấy buồn hôm nay"},
                {"role": "assistant", "content": "Tôi hiểu bạn đang cảm thấy buồn. Có điều gì đặc biệt khiến bạn cảm thấy như vậy?"},
                {"role": "user", "content": "Công việc khó khăn quá"}
            ]
            
            contextual_response = rag.generate_contextual_response(
                "Làm sao để tôi cảm thấy tốt hơn?",
                chat_history
            )
            print(f"💬 Contextual Response: {contextual_response}")
        except Exception as e:
            print(f"❌ Contextual response error: {str(e)}")
        
        print("\n✅ RAG System Testing Complete!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()

def test_fallback_response():
    """Test fallback response when vector DB is not available."""
    
    print("\n🧪 TESTING FALLBACK RESPONSE")
    print("=" * 50)
    
    try:
        # Create RAG system with non-existent DB path
        rag = DiaryRAGSystem(
            vector_db_path="./non_existent_path",
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        # Test fallback response
        response = rag.generate_response("Tôi cảm thấy buồn", use_fallback=True)
        print(f"🤖 Fallback Response: {response}")
        
        print("✅ Fallback response works!")
        
    except Exception as e:
        print(f"❌ Fallback test error: {str(e)}")

if __name__ == "__main__":
    # Check for Google API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("⚠️ Warning: GOOGLE_API_KEY environment variable not set")
        print("Some tests may fail without the API key")
    
    # Run tests
    test_rag_system()
    test_fallback_response()
    
    print("\n🎉 All tests completed!")
    print("\nUsage in interface.py:")
    print("```python")
    print("from Retrivel_And_Generation.Retrieval_And_Generator import create_rag_system")
    print("")
    print("# Initialize RAG system")
    print("rag = create_rag_system()")
    print("")
    print("# Generate response")
    print("response = rag.generate_response(user_query)")
    print("```")
