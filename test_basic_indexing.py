"""
Test script đơn giản để kiểm tra chức năng indexing 
"""
import sys
import os

# Đảm bảo sử dụng đúng environment path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src', 'streamlit_app')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src', 'Indexingstep')))

def test_basic_indexing():
    """Test basic functionality"""
    print("Testing basic indexing functionality...")
    
    # Test 1: Import check
    try:
        from dataloading import DiaryDataLoader
        print("✅ DiaryDataLoader import successful")
    except ImportError as e:
        print(f"❌ DiaryDataLoader import failed: {e}")
        return False
    
    # Test 2: Database connection
    try:
        db_path = os.path.join("src", "streamlit_app", "backend", "diary.db")
        if os.path.exists(db_path):
            print(f"✅ Database found: {db_path}")
            
            # Test loading data
            loader = DiaryDataLoader(db_path=db_path)
            documents = loader.load()
            print(f"✅ Loaded {len(documents)} diary entries")
            
            # Show sample
            if documents:
                print(f"Sample entry: {documents[0].page_content[:50]}...")
            
        else:
            print(f"❌ Database not found: {db_path}")
            return False
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    # Test 3: Environment file
    try:
        env_path = os.path.join("src", "Indexingstep", ".env")
        if os.path.exists(env_path):
            print(f"✅ Environment file found: {env_path}")
            
            # Check for API key
            from dotenv import load_dotenv
            load_dotenv(env_path)
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                print(f"✅ Google API key configured")
            else:
                print(f"⚠️ Google API key not found")
        else:
            print(f"❌ Environment file not found: {env_path}")
            
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("DIARY INDEXING TEST")
    print("=" * 50)
    
    success = test_basic_indexing()
    
    print("=" * 50)
    if success:
        print("✅ Basic tests passed!")
        print("🔍 Your indexing setup should work correctly.")
        print("📝 Try adding a new diary entry through the Streamlit app to test automatic indexing.")
    else:
        print("❌ Some tests failed!")
        print("🔧 Please check the error messages above.")
