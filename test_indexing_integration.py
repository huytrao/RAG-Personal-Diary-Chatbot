"""
Test script để kiểm tra chức năng indexing tự động
"""
import os
import sys

# Add path để import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'Indexingstep'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'streamlit_app'))

def test_incremental_indexing():
    """Test incremental indexing functionality"""
    try:
        from src.Indexingstep.pipeline import DiaryIndexingPipeline
        from dotenv import load_dotenv
        from datetime import datetime, timedelta
        
        # Load environment config
        load_dotenv(os.path.join('src', 'Indexingstep', '.env'))
        
        config = {
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "db_path": os.path.join("src", "streamlit_app", "backend", "diary.db"),
            "persist_directory": os.path.join("src", "Indexingstep", "diary_vector_db"),
            "collection_name": "diary_entries",
            "embedding_model": "models/embedding-001",
            "chunk_size": 800,
            "chunk_overlap": 100,
            "batch_size": 50
        }
        
        print("Configuration:")
        for key, value in config.items():
            if 'api_key' in key:
                print(f"  {key}: {'***' if value else 'Not set'}")
            else:
                print(f"  {key}: {value}")
        
        # Check if API key exists
        if not config["google_api_key"]:
            print("❌ Google API key not found!")
            return False
            
        # Check if database exists
        if not os.path.exists(config["db_path"]):
            print(f"❌ Database not found: {config['db_path']}")
            return False
            
        print("✅ All requirements met!")
        
        # Initialize pipeline
        print("🔄 Initializing pipeline...")
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
        
        # Test incremental update
        print("🔄 Running incremental update...")
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        
        results = pipeline.incremental_update(
            start_date=start_date,
            end_date=end_date
        )
        
        print(f"✅ Indexing completed!")
        print(f"Results: {results}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testing incremental indexing functionality...")
    print("=" * 50)
    success = test_incremental_indexing()
    print("=" * 50)
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")
