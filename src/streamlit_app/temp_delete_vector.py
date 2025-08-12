
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "Indexingstep"))

from embedding_and_storing import DiaryEmbeddingAndStorage
from dotenv import load_dotenv

# Load environment config
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "Indexingstep", ".env"))

config = {
    "google_api_key": os.getenv("GOOGLE_API_KEY"),
    "persist_directory": os.path.join(os.path.dirname(__file__), "..", "Indexingstep", "diary_vector_db"),
    "collection_name": "diary_entries",
    "embedding_model": "models/embedding-001"
}

if config["google_api_key"]:
    try:
        # Initialize embedding storage
        embedding_storage = DiaryEmbeddingAndStorage(
            api_key=config["google_api_key"],
            persist_directory=config["persist_directory"],
            collection_name=config["collection_name"],
            embedding_model=config["embedding_model"]
        )
        
        # Remove documents with matching date and title
        filter_criteria = {
            "date": "2025-08-12",
            "title": "Helloo"
        }
        
        success = embedding_storage.delete_documents_by_metadata(filter_criteria)
        print(f"Vector database deletion: {success}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
else:
    print("No API key found")
    sys.exit(1)
