#!/usr/bin/env python3
"""
Debug script to check vector database status
"""
import os
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Set API key
os.environ['GOOGLE_API_KEY'] = 'AIzaSyAZQN21CjLySEybT6vOYDCz4V_e85gD42k'

def debug_vector_db():
    print("🔍 DEBUGGING VECTOR DATABASE")
    print("=" * 50)
    
    # Check directory structure
    db_path = "src/Indexingstep/diary_vector_db_enhanced"
    print(f"📂 Database path: {db_path}")
    print(f"📂 Path exists: {os.path.exists(db_path)}")
    
    if os.path.exists(db_path):
        print(f"📁 Directory contents:")
        for item in os.listdir(db_path):
            item_path = os.path.join(db_path, item)
            print(f"   - {item} ({'dir' if os.path.isdir(item_path) else 'file'})")
    
    # Try to connect with default collection
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model='models/embedding-001')
        
        # Try default collection name
        vector_store = Chroma(
            persist_directory=db_path, 
            embedding_function=embeddings
        )
        docs = vector_store.get()
        print(f"📊 Default collection: {len(docs['ids'])} documents")
        
        # Try specific collection name
        vector_store_named = Chroma(
            persist_directory=db_path, 
            embedding_function=embeddings,
            collection_name="diary_entries"
        )
        docs_named = vector_store_named.get()
        print(f"📊 'diary_entries' collection: {len(docs_named['ids'])} documents")
        
        # List all collections
        import chromadb
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        print(f"📋 Available collections: {[c.name for c in collections]}")
        
        if collections:
            for collection in collections:
                count = collection.count()
                print(f"   - {collection.name}: {count} documents")
        
    except Exception as e:
        print(f"❌ Error connecting to vector database: {e}")

if __name__ == "__main__":
    debug_vector_db()
