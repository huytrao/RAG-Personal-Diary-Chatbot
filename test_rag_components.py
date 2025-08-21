#!/usr/bin/env python3
"""
Simple test to isolate where the timeout is occurring
"""
import sys
import os
import time
from datetime import datetime

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
sys.path.append(src_dir)
sys.path.append(os.path.join(src_dir, "Indexingstep"))
sys.path.append(os.path.join(src_dir, "Retrivel_And_Generation"))

def test_rag_components():
    """Test each RAG component individually"""
    
    print("🧪 Testing RAG System Components")
    print("=" * 50)
    
    # Test 1: Import modules
    print("1️⃣ Testing imports...")
    start = time.time()
    try:
        from Retrivel_And_Generation.Retrieval_And_Generator import create_rag_system, DiaryRAGSystem
        print(f"✅ Imports successful ({time.time() - start:.2f}s)")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 2: Create RAG system (this loads vector DB)
    print("\n2️⃣ Testing RAG system creation...")
    start = time.time()
    try:
        user_id = 1
        base_vector_path = os.path.join(current_dir, "VectorDB")
        
        # Load API key from .env
        from dotenv import load_dotenv
        load_dotenv()
        google_api_key = os.getenv("GOOGLE_API_KEY")
        
        print(f"   Vector path: {base_vector_path}")
        print(f"   API key configured: {bool(google_api_key)}")
        
        rag_system = create_rag_system(
            user_id=user_id,
            base_vector_path=base_vector_path,
            google_api_key=google_api_key
        )
        
        if rag_system:
            print(f"✅ RAG system created ({time.time() - start:.2f}s)")
        else:
            print(f"❌ RAG system creation returned None ({time.time() - start:.2f}s)")
            return False
            
    except Exception as e:
        print(f"❌ RAG system creation failed ({time.time() - start:.2f}s): {e}")
        return False
    
    # Test 3: Simple retrieval (no LLM)
    print("\n3️⃣ Testing document retrieval...")
    start = time.time()
    try:
        docs = rag_system.retrieve_relevant_entries("hello", k=1)
        print(f"✅ Retrieved {len(docs)} documents ({time.time() - start:.2f}s)")
    except Exception as e:
        print(f"❌ Retrieval failed ({time.time() - start:.2f}s): {e}")
        return False
    
    # Test 4: Fast response (minimal LLM call)
    print("\n4️⃣ Testing fast response generation...")
    start = time.time()
    try:
        response = rag_system.generate_fast_response("hello")
        print(f"✅ Fast response generated ({time.time() - start:.2f}s)")
        print(f"   Response: {response[:50]}...")
    except Exception as e:
        print(f"❌ Fast response failed ({time.time() - start:.2f}s): {e}")
        return False
    
    # Test 5: Contextual response (full LLM call)
    print("\n5️⃣ Testing contextual response generation...")
    start = time.time()
    try:
        response = rag_system.generate_contextual_response("hello", [])
        print(f"✅ Contextual response generated ({time.time() - start:.2f}s)")
        print(f"   Response: {response[:50]}...")
    except Exception as e:
        print(f"❌ Contextual response failed ({time.time() - start:.2f}s): {e}")
        return False
    
    print("\n🎉 All tests passed!")
    return True

if __name__ == "__main__":
    test_rag_components()
