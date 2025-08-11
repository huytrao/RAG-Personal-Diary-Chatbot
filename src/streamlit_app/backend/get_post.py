import requests
import streamlit as st
from typing import List, Dict, Any

# API configuration
API_BASE_URL = "http://127.0.0.1:8000"

def check_api_connection() -> bool:
    """Check if the API is running and accessible"""
    try:
        response = requests.get(f"{API_BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def submit_text_to_database(entry: Dict[str, Any]) -> bool:
    """
    Submit diary entry to the database via FastAPI.
    """
    try:
        # Check API connection first
        if not check_api_connection():
            st.error("❌ API server is not running. Please start the FastAPI server.")
            return False
        
        # Validate entry data
        if not entry.get('date') or not entry.get('content'):
            st.error("❌ Invalid entry data: missing date or content")
            return False
        
        # Combine title, type and content for the API
        title = entry.get('title', 'Untitled')
        entry_type = entry.get('type', 'Text')
        content = entry.get('content', '')
        
        full_content = f"Title: {title}\nType: {entry_type}\nContent: {content}"
        
        payload = {
            "date": entry["date"],
            "content": full_content
        }
        
        response = requests.post(
            f"{API_BASE_URL}/submit_diary",
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            st.success("✅ Diary entry saved to database successfully!")
            return True
        else:
            try:
                error_detail = response.json().get('detail', 'Unknown error')
            except:
                error_detail = response.text
            st.error(f"API Error: {response.status_code} - {error_detail}")
            return False
            
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API. Make sure FastAPI server is running on http://127.0.0.1:8000")
        return False
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {str(e)}")
        return False
    except Exception as e:
        st.error(f"Unexpected Error: {str(e)}")
        return False

def load_entries_from_database() -> List[Dict[str, Any]]:
    """
    Load diary entries from the database via FastAPI.
    """
    try:
        # Check API connection first
        if not check_api_connection():
            st.warning("⚠️ API server not available. Using sample data.")
            return get_sample_data()
        
        response = requests.get(f"{API_BASE_URL}/entries", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            entries = []
            
            for entry in data.get("entries", []):
                # Parse the combined content back into components
                content_lines = entry["content"].split("\n")
                title = "Untitled"
                entry_type = "Text"
                content = entry["content"]
                
                # Extract title and type if they exist
                for line in content_lines:
                    if line.startswith("Title: "):
                        title = line.replace("Title: ", "").strip()
                    elif line.startswith("Type: "):
                        entry_type = line.replace("Type: ", "").strip()
                    elif line.startswith("Content: "):
                        content = line.replace("Content: ", "").strip()
                
                entries.append({
                    "id": entry["id"],
                    "date": entry["date"],
                    "title": title,
                    "content": content,
                    "type": entry_type,
                    "created_at": entry.get("created_at")
                })
            
            return entries if entries else get_sample_data()
        else:
            st.warning(f"Failed to load entries from API: {response.status_code}")
            return get_sample_data()
            
    except requests.exceptions.ConnectionError:
        st.warning("⚠️ Cannot connect to database API. Using sample data.")
        return get_sample_data()
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {str(e)}")
        return get_sample_data()
    except Exception as e:
        st.error(f"Error loading entries: {str(e)}")
        return get_sample_data()

def get_sample_data() -> List[Dict[str, Any]]:
    """Return sample diary entries when database is not available"""
    return [
        {"date": "2025-08-01", "title": "Welcome to Huy Trao Personal project", "content": "Tks for your visit at Huy Trao Personal project", "type": "Text"},
        {"date": "2025-08-02", "title": "How to use this chatbot", "content": "Went to the gym for 1 hour.", "type": "Text"},
        {"date": "2025-08-03", "title": "Let's contact together", "content": "Read 50 pages of a book.", "type": "Text"},
    ]