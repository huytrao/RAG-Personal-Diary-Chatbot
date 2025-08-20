import requests
import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class RAGServiceClient:
    """Client to interact with RAG FastAPI service."""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8002"):
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> bool:
        """Check if RAG service is running."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """Get RAG system status for user."""
        try:
            response = requests.get(f"{self.base_url}/users/{user_id}/status", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting user status: {e}")
            return {"status": "error", "error": str(e)}
    
    def index_user_data(
        self, 
        user_id: int, 
        clear_existing: bool = False,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """Index user's diary data."""
        try:
            payload = {
                "user_id": user_id,
                "clear_existing": clear_existing
            }
            
            if start_date:
                payload["start_date"] = start_date
            if end_date:
                payload["end_date"] = end_date
            
            response = requests.post(
                f"{self.base_url}/users/{user_id}/index",
                json=payload,
                timeout=300  # 5 minutes for indexing
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error indexing user data: {e}")
            return {"status": "error", "error": str(e)}
    
    def query_rag(
        self,
        user_id: int,
        query: str,
        fast_mode: bool = False,
        chat_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Query RAG system."""
        try:
            payload = {
                "user_id": user_id,
                "query": query,
                "fast_mode": fast_mode,
                "chat_history": chat_history or []
            }
            
            response = requests.post(
                f"{self.base_url}/users/{user_id}/query",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error querying RAG: {e}")
            return {"status": "error", "error": str(e)}
    
    def incremental_sync(self, user_id: int, start_date: str = None) -> Dict[str, Any]:
        """Run incremental sync."""
        try:
            params = {}
            if start_date:
                params["start_date"] = start_date
            
            response = requests.post(
                f"{self.base_url}/users/{user_id}/incremental-index",
                params=params,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in incremental sync: {e}")
            return {"status": "error", "error": str(e)}
    
    def clear_cache(self, user_id: int) -> Dict[str, Any]:
        """Clear user cache."""
        try:
            response = requests.delete(f"{self.base_url}/users/{user_id}/cache", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"status": "error", "error": str(e)}
    
    def delete_vector_db(self, user_id: int) -> Dict[str, Any]:
        """Delete user's vector database."""
        try:
            response = requests.delete(f"{self.base_url}/users/{user_id}/vector-db", timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error deleting vector DB: {e}")
            return {"status": "error", "error": str(e)}
    
    def check_ai_availability(self, user_id: int) -> Dict[str, Any]:
        """Check AI availability and get detailed status."""
        try:
            response = requests.get(f"{self.base_url}/users/{user_id}/ai-availability", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error checking AI availability: {e}")
            return {"overall_status": "error", "error": str(e)}
    
    def fix_ai_availability(self, user_id: int) -> Dict[str, Any]:
        """Attempt to fix AI availability issues."""
        try:
            response = requests.post(f"{self.base_url}/users/{user_id}/fix-ai-availability", timeout=120)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fixing AI availability: {e}")
            return {"status": "error", "error": str(e)}
    
    def auto_index_new_entry(self, user_id: int) -> Dict[str, Any]:
        """Auto-index after saving new diary entry."""
        try:
            response = requests.post(
                f"{self.base_url}/users/{user_id}/auto-index-new-entry",
                timeout=120  # 2 minutes for indexing
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error in auto-index: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        try:
            response = requests.get(f"{self.base_url}/stats", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"status": "error", "error": str(e)}
