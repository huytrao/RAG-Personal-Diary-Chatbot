"""
Test script to add diary entries with multiple tags to test the tag functionality.
"""
import requests
import json
from datetime import datetime, timedelta

API_BASE_URL = "http://127.0.0.1:8000"

def add_test_entries():
    """Add several test entries with different tag combinations"""
    
    test_entries = [
        {
            "date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "title": "Morning Workout Session",
            "content": "Title: Morning Workout Session\nType: Text\nContent: Had a great workout this morning! Feeling energized and ready for the day. #fitness #morning #health #motivation",
            "tags": "fitness,morning,health,motivation"
        },
        {
            "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
            "title": "Work Project Completion",
            "content": "Title: Work Project Completion\nType: Text\nContent: Finally completed the big project at work today. Team collaboration was excellent! #work #achievement #teamwork #project #success",
            "tags": "work,achievement,teamwork,project,success"
        },
        {
            "date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
            "title": "Family Dinner",
            "content": "Title: Family Dinner\nType: Text\nContent: Beautiful family dinner tonight. Mom made her famous pasta and we shared stories. #family #food #love #memories #happiness",
            "tags": "family,food,love,memories,happiness"
        },
        {
            "date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
            "title": "Learning New Technology",
            "content": "Title: Learning New Technology\nType: Text\nContent: Started learning React today. It's challenging but exciting! #learning #programming #react #technology #growth #development",
            "tags": "learning,programming,react,technology,growth,development"
        },
        {
            "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "title": "Weekend Travel",
            "content": "Title: Weekend Travel\nType: Text\nContent: Amazing weekend trip to the mountains. Fresh air, beautiful views, and great company! #travel #nature #mountains #weekend #adventure #relaxation",
            "tags": "travel,nature,mountains,weekend,adventure,relaxation"
        }
    ]
    
    print("Adding test entries with multiple tags...")
    for entry in test_entries:
        try:
            response = requests.post(
                f"{API_BASE_URL}/submit_diary",
                json={
                    "date": entry["date"],
                    "content": entry["content"],
                    "tags": entry["tags"]
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Added: {entry['title']} with tags: {entry['tags']}")
            else:
                print(f"❌ Failed to add: {entry['title']} - {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error adding {entry['title']}: {str(e)}")
    
    print("\n🎉 Test entries added! You can now test the tag filtering in the Streamlit app.")
    print("Tags available for testing:")
    all_tags = set()
    for entry in test_entries:
        tags = entry["tags"].split(",")
        all_tags.update(tags)
    
    for tag in sorted(all_tags):
        print(f"  - #{tag}")

if __name__ == "__main__":
    add_test_entries()
