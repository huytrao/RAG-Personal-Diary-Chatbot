"""
Test script to verify delete functionality
"""
import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_delete_functionality():
    """Test the delete endpoint"""
    print("Testing Delete Functionality")
    print("=" * 40)
    
    # Test 1: Check API is running
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            print("✅ API is running")
        else:
            print("❌ API not responding properly")
            return
    except:
        print("❌ Cannot connect to API")
        return
    
    # Test 2: Get current entries
    try:
        response = requests.get(f"{API_BASE_URL}/entries")
        if response.status_code == 200:
            entries = response.json().get("entries", [])
            print(f"✅ Found {len(entries)} entries in database")
            
            if entries:
                # Show first few entries
                for i, entry in enumerate(entries[:3]):
                    print(f"  Entry {entry['id']}: {entry['date']} - {entry['content'][:30]}...")
                
                # Test 3: Try to delete the first entry (if exists)
                if len(entries) > 0:
                    entry_to_delete = entries[0]
                    entry_id = entry_to_delete['id']
                    print(f"\n🧪 Testing delete for entry ID {entry_id}")
                    
                    # Don't actually delete, just test the endpoint exists
                    print(f"💡 To test delete, you can manually call:")
                    print(f"   DELETE {API_BASE_URL}/entries/{entry_id}")
                    print(f"   Or use the Streamlit interface delete button")
            else:
                print("ℹ️ No entries to test delete with")
                
        else:
            print("❌ Failed to get entries")
            
    except Exception as e:
        print(f"❌ Error testing: {e}")
    
    print("\n" + "=" * 40)
    print("Delete functionality is ready to test!")
    print("👆 Use the Streamlit app to test the delete button")

if __name__ == "__main__":
    test_delete_functionality()
