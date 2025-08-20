import os
import sys
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

def create_user_vector_database(user_id: int, diary_entries: List[Dict[str, Any]]) -> bool:
    """
    Create vector database for a specific user from their diary entries.
    
    Args:
        user_id: User ID
        diary_entries: List of diary entries from database
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Setup paths
        base_vector_path = os.path.dirname(os.path.abspath(__file__))
        vector_db_path = os.path.join(base_vector_path, f"user_{user_id}_vector_db")
        collection_name = f"user_{user_id}_diary_entries"
        
        # Create directory
        os.makedirs(vector_db_path, exist_ok=True)
        
        # Initialize embeddings
        google_api_key = os.getenv("GOOGLE_API_KEY")
        if not google_api_key:
            raise ValueError("Google API key not found")
            
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        
        # Process diary entries into documents
        documents = []
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        for entry in diary_entries:
            # Extract content
            content = entry.get('content', '')
            if not content:
                continue
                
            # Extract title and content
            lines = content.split('\n')
            title = "Untitled"
            actual_content = content
            
            for line in lines:
                if line.startswith('Title: '):
                    title = line.replace('Title: ', '').strip()
                elif line.startswith('Content: '):
                    actual_content = line.replace('Content: ', '').strip()
                    break
            
            # Create metadata
            metadata = {
                'user_id': user_id,
                'entry_id': entry.get('id'),
                'date': entry.get('date', ''),
                'title': title,
                'tags': entry.get('tags', ''),
                'tags_list': [tag.strip() for tag in entry.get('tags', '').split(',') if tag.strip()],
                'source': f"diary_entry_{entry.get('id')}"
            }
            
            # Split content if too long
            if len(actual_content) > 1000:
                chunks = text_splitter.split_text(actual_content)
                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata['chunk_id'] = i
                    documents.append(Document(page_content=chunk, metadata=chunk_metadata))
            else:
                documents.append(Document(page_content=actual_content, metadata=metadata))
        
        if not documents:
            print(f"No documents to index for user {user_id}")
            return False
        
        # Create vector store
        vector_store = Chroma(
            persist_directory=vector_db_path,
            embedding_function=embeddings,
            collection_name=collection_name
        )
        
        # Add documents to vector store
        vector_store.add_documents(documents)
        
        # Persist the database
        vector_store.persist()
        
        print(f"Successfully created vector database for user {user_id} with {len(documents)} documents")
        return True
        
    except Exception as e:
        print(f"Error creating vector database for user {user_id}: {e}")
        return False
