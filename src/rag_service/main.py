from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import sys
import uvicorn
from datetime import datetime
import json
import logging

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
sys.path.append(src_dir)
sys.path.append(os.path.join(src_dir, "Indexingstep"))
sys.path.append(os.path.join(src_dir, "Retrivel_And_Generation"))

# Import your modules
try:
    from Indexingstep.pipeline import DiaryIndexingPipeline
    from Retrivel_And_Generation.Retrieval_And_Generator import create_rag_system, DiaryRAGSystem
    RAG_MODULES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RAG modules not available: {e}")
    RAG_MODULES_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Personal Diary RAG Service",
    description="RAG service for personal diary chatbot with user isolation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for RAG systems
rag_systems_cache: Dict[int, DiaryRAGSystem] = {}

# ========================================
# PYDANTIC MODELS
# ========================================

class DiaryEntry(BaseModel):
    date: str
    content: str
    tags: str = ""

class IndexRequest(BaseModel):
    user_id: int
    clear_existing: bool = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class QueryRequest(BaseModel):
    user_id: int
    query: str
    fast_mode: bool = False
    chat_history: List[Dict[str, str]] = []

class UserStatusResponse(BaseModel):
    user_id: int
    status: str
    document_count: int
    vector_db_path: str
    last_updated: Optional[str] = None
    error: Optional[str] = None

class QueryResponse(BaseModel):
    user_id: int
    response: str
    processing_time: float
    documents_used: int
    fast_mode: bool

class IndexResponse(BaseModel):
    user_id: int
    status: str
    documents_processed: int
    chunks_created: int
    vector_db_path: str
    processing_time: float
    error: Optional[str] = None

# ========================================
# HELPER FUNCTIONS
# ========================================

def get_user_paths(user_id: int) -> Dict[str, str]:
    """Get all paths for a user."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return {
        "vector_db_path": os.path.join(base_dir, "VectorDB", f"user_{user_id}_vector_db"),
        "diary_db_path": os.path.join(base_dir, "streamlit_app", "backend", f"user_{user_id}_diary.db"),
        "base_vector_path": os.path.join(base_dir, "VectorDB")
    }

def get_pipeline_config(user_id: int) -> Dict[str, Any]:
    """Get configuration for DiaryIndexingPipeline."""
    paths = get_user_paths(user_id)
    
    return {
        "db_path": paths["diary_db_path"],
        "persist_directory": paths["vector_db_path"],
        "collection_name": f"user_{user_id}_diary_entries",
        "google_api_key": os.getenv("GOOGLE_API_KEY"),
        "chunk_size": 800,
        "chunk_overlap": 100,
        "batch_size": 50,
        "user_id": user_id
    }

def check_vector_db_exists(user_id: int) -> bool:
    """Check if vector database exists for user."""
    paths = get_user_paths(user_id)
    return os.path.exists(paths["vector_db_path"])

def get_document_count(user_id: int) -> int:
    """Get document count from vector database."""
    try:
        if user_id in rag_systems_cache:
            return rag_systems_cache[user_id].get_document_count()
        
        if not check_vector_db_exists(user_id):
            return 0
        
        # Create temporary RAG system to check count
        paths = get_user_paths(user_id)
        temp_rag = create_rag_system(
            user_id=user_id,
            base_vector_path=paths["base_vector_path"],
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        if temp_rag:
            return temp_rag.get_document_count()
        return 0
        
    except Exception as e:
        logger.error(f"Error getting document count for user {user_id}: {e}")
        return 0

def get_or_create_rag_system(user_id: int) -> DiaryRAGSystem:
    """Get existing RAG system or create new one."""
    if user_id not in rag_systems_cache:
        if not check_vector_db_exists(user_id):
            raise HTTPException(
                status_code=404,
                detail=f"Vector database not found for user {user_id}. Please run indexing first."
            )
        
        paths = get_user_paths(user_id)
        rag_system = create_rag_system(
            user_id=user_id,
            base_vector_path=paths["base_vector_path"],
            google_api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        if not rag_system:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create RAG system for user {user_id}"
            )
        
        rag_systems_cache[user_id] = rag_system
        logger.info(f"Created RAG system for user {user_id}")
    
    return rag_systems_cache[user_id]

# ========================================
# API ENDPOINTS
# ========================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "message": "Personal Diary RAG Service is running",
        "version": "1.0.0",
        "cached_users": list(rag_systems_cache.keys()),
        "vector_db_base": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VectorDB")
    }

@app.get("/health")
async def health_check():
    """Detailed health check."""
    try:
        google_api_key = os.getenv("GOOGLE_API_KEY")
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vector_db_base = os.path.join(base_dir, "VectorDB")
        
        return {
            "status": "healthy",
            "google_api_configured": bool(google_api_key),
            "vector_db_base_exists": os.path.exists(vector_db_base),
            "cached_users": list(rag_systems_cache.keys()),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@app.get("/users/{user_id}/ai-availability")
async def check_ai_availability(user_id: int):
    """Check AI availability and provide detailed status for troubleshooting."""
    try:
        # Check all prerequisites for AI availability
        availability_info = {
            "user_id": user_id,
            "overall_status": "checking",
            "checks": {
                "rag_modules": {
                    "available": RAG_MODULES_AVAILABLE,
                    "status": "✅ Available" if RAG_MODULES_AVAILABLE else "❌ Not Available",
                    "details": "Required modules: DiaryIndexingPipeline, DiaryRAGSystem"
                },
                "google_api_key": {
                    "configured": bool(os.getenv("GOOGLE_API_KEY")),
                    "status": "✅ Configured" if os.getenv("GOOGLE_API_KEY") else "❌ Not Configured",
                    "details": "Required for embeddings and LLM responses"
                },
                "vector_database": {
                    "exists": check_vector_db_exists(user_id),
                    "status": "✅ Exists" if check_vector_db_exists(user_id) else "⚠️ Not Found",
                    "path": get_user_paths(user_id)["vector_db_path"]
                },
                "document_count": {
                    "count": get_document_count(user_id),
                    "status": "✅ Has Documents" if get_document_count(user_id) > 0 else "⚠️ Empty",
                    "details": f"{get_document_count(user_id)} documents indexed"
                }
            },
            "recommendations": [],
            "actions": []
        }
        
        # Determine overall status and recommendations
        if not RAG_MODULES_AVAILABLE:
            availability_info["overall_status"] = "unavailable"
            availability_info["recommendations"].append("Install missing RAG modules")
            availability_info["actions"].append({
                "action": "check_imports",
                "description": "Verify DiaryIndexingPipeline and DiaryRAGSystem imports"
            })
        elif not os.getenv("GOOGLE_API_KEY"):
            availability_info["overall_status"] = "not_configured"
            availability_info["recommendations"].append("Configure Google API key")
            availability_info["actions"].append({
                "action": "set_api_key",
                "description": "Add GOOGLE_API_KEY to environment variables"
            })
        elif not check_vector_db_exists(user_id):
            availability_info["overall_status"] = "needs_indexing"
            availability_info["recommendations"].append("Create vector database for user")
            availability_info["actions"].append({
                "action": "initial_index",
                "endpoint": f"/users/{user_id}/auto-index-new-entry",
                "description": "Run initial indexing to create vector database"
            })
        elif get_document_count(user_id) == 0:
            availability_info["overall_status"] = "empty_database"
            availability_info["recommendations"].append("Add diary entries or rebuild index")
            availability_info["actions"].append({
                "action": "check_diary_entries",
                "description": "Verify user has diary entries in database"
            })
            availability_info["actions"].append({
                "action": "rebuild_index",
                "endpoint": f"/users/{user_id}/auto-index-new-entry",
                "description": "Rebuild vector database from existing entries"
            })
        else:
            availability_info["overall_status"] = "available"
            availability_info["recommendations"].append("AI is ready for use")
            availability_info["actions"].append({
                "action": "query_ready",
                "endpoint": f"/users/{user_id}/query",
                "description": "AI is ready to answer questions"
            })
        
        # Add cache status
        availability_info["cache_status"] = {
            "user_cached": user_id in rag_systems_cache,
            "total_cached_users": len(rag_systems_cache),
            "cached_users": list(rag_systems_cache.keys())
        }
        
        return availability_info
        
    except Exception as e:
        logger.error(f"Error checking AI availability for user {user_id}: {e}")
        return {
            "user_id": user_id,
            "overall_status": "error",
            "error": str(e),
            "recommendations": ["Check service logs for detailed error information"],
            "actions": [{
                "action": "check_logs",
                "description": "Review service logs for error details"
            }]
        }

@app.post("/users/{user_id}/fix-ai-availability")
async def fix_ai_availability(user_id: int):
    """Attempt to automatically fix AI availability issues."""
    try:
        if not RAG_MODULES_AVAILABLE:
            return {
                "status": "cannot_fix",
                "reason": "RAG modules not available - requires code/environment fix",
                "action_needed": "Install missing Python modules"
            }
        
        if not os.getenv("GOOGLE_API_KEY"):
            return {
                "status": "cannot_fix", 
                "reason": "Google API key not configured",
                "action_needed": "Set GOOGLE_API_KEY environment variable"
            }
        
        # Try to fix vector database issues
        if not check_vector_db_exists(user_id) or get_document_count(user_id) == 0:
            logger.info(f"Attempting to fix AI availability for user {user_id}")
            
            # Clear cache first
            if user_id in rag_systems_cache:
                del rag_systems_cache[user_id]
            
            # Create/rebuild vector database
            config = get_pipeline_config(user_id)
            paths = get_user_paths(user_id)
            os.makedirs(os.path.dirname(paths["vector_db_path"]), exist_ok=True)
            
            pipeline = DiaryIndexingPipeline(**config)
            results = pipeline.run_full_pipeline(clear_existing=True)
            
            if results.get('status') == 'completed_successfully':
                doc_count = get_document_count(user_id)
                return {
                    "status": "fixed",
                    "action_taken": "Created/rebuilt vector database",
                    "documents_processed": results.get('documents_loaded', 0),
                    "chunks_created": results.get('chunks_created', 0),
                    "final_document_count": doc_count,
                    "ai_status": "ready" if doc_count > 0 else "empty"
                }
            else:
                return {
                    "status": "fix_failed",
                    "reason": "Failed to create vector database",
                    "error": results.get('errors', 'Unknown error')
                }
        else:
            return {
                "status": "already_available",
                "message": "AI is already available for this user",
                "document_count": get_document_count(user_id)
            }
            
    except Exception as e:
        logger.error(f"Error fixing AI availability for user {user_id}: {e}")
        return {
            "status": "error",
            "error": str(e),
            "action_needed": "Check service logs and try manual troubleshooting"
        }

@app.get("/users/{user_id}/status", response_model=UserStatusResponse)
async def get_user_status(user_id: int):
    """Get RAG system status for a user."""
    try:
        paths = get_user_paths(user_id)
        
        if not check_vector_db_exists(user_id):
            return UserStatusResponse(
                user_id=user_id,
                status="not_indexed",
                document_count=0,
                vector_db_path=paths["vector_db_path"]
            )
        
        doc_count = get_document_count(user_id)
        
        return UserStatusResponse(
            user_id=user_id,
            status="ready" if doc_count > 0 else "empty",
            document_count=doc_count,
            vector_db_path=paths["vector_db_path"],
            last_updated=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error getting status for user {user_id}: {e}")
        return UserStatusResponse(
            user_id=user_id,
            status="error",
            document_count=0,
            vector_db_path="",
            error=str(e)
        )

@app.post("/users/{user_id}/index", response_model=IndexResponse)
async def index_user_data(user_id: int, request: IndexRequest, background_tasks: BackgroundTasks):
    """Index diary entries for a user."""
    start_time = datetime.now()
    
    try:
        # Ensure VectorDB directory exists
        paths = get_user_paths(user_id)
        os.makedirs(os.path.dirname(paths["vector_db_path"]), exist_ok=True)
        
        # Get pipeline configuration
        config = get_pipeline_config(user_id)
        
        logger.info(f"Starting indexing for user {user_id} with config: {config}")
        
        # Create and run pipeline
        pipeline = DiaryIndexingPipeline(**config)
        
        if request.start_date and request.end_date:
            # Date range indexing
            results = pipeline.run_full_pipeline(
                start_date=request.start_date,
                end_date=request.end_date,
                clear_existing=request.clear_existing
            )
        else:
            # Full indexing
            results = pipeline.run_full_pipeline(clear_existing=request.clear_existing)
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if results.get('status') == 'completed_successfully':
            # Clear cache to force reload
            if user_id in rag_systems_cache:
                del rag_systems_cache[user_id]
            
            return IndexResponse(
                user_id=user_id,
                status="success",
                documents_processed=results.get('documents_loaded', 0),
                chunks_created=results.get('chunks_created', 0),
                vector_db_path=paths["vector_db_path"],
                processing_time=processing_time
            )
        else:
            return IndexResponse(
                user_id=user_id,
                status="failed",
                documents_processed=0,
                chunks_created=0,
                vector_db_path=paths["vector_db_path"],
                processing_time=processing_time,
                error=results.get('errors', 'Unknown error')
            )
            
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"Indexing error for user {user_id}: {e}")
        
        return IndexResponse(
            user_id=user_id,
            status="error",
            documents_processed=0,
            chunks_created=0,
            vector_db_path="",
            processing_time=processing_time,
            error=str(e)
        )

@app.post("/users/{user_id}/incremental-index")
async def incremental_index(user_id: int, start_date: str = None):
    """Run incremental indexing for user."""
    try:
        config = get_pipeline_config(user_id)
        pipeline = DiaryIndexingPipeline(**config)
        
        if start_date:
            results = pipeline.incremental_update(start_date)
        else:
            # Default to last 7 days
            from datetime import timedelta
            default_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            results = pipeline.incremental_update(default_start)
        
        if results.get('status') == 'success':
            # Clear cache to force reload
            if user_id in rag_systems_cache:
                del rag_systems_cache[user_id]
            
            return {
                "user_id": user_id,
                "status": "success",
                "documents_added": results.get('documents_added', 0),
                "start_date": start_date or default_start
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Incremental indexing failed: {results.get('error', 'Unknown error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Incremental indexing error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/users/{user_id}/query", response_model=QueryResponse)
async def query_user_rag(user_id: int, request: QueryRequest):
    """Query RAG system for a user."""
    start_time = datetime.now()
    
    try:
        # Get or create RAG system
        rag_system = get_or_create_rag_system(user_id)
        
        # Generate response
        if request.fast_mode:
            response = rag_system.generate_fast_response(query=request.query)
        else:
            response = rag_system.generate_contextual_response(
                query=request.query,
                chat_history=request.chat_history
            )
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return QueryResponse(
            user_id=user_id,
            response=response,
            processing_time=processing_time,
            documents_used=5,  # Default retrieval count
            fast_mode=request.fast_mode
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@app.post("/users/{user_id}/auto-index-new-entry")
async def auto_index_new_entry(user_id: int):
    """Auto-index after saving new diary entry. Creates initial index if not exists."""
    try:
        if not RAG_MODULES_AVAILABLE:
            return {"status": "skipped", "reason": "RAG modules not available"}
        
        # Check if vector DB exists
        if not check_vector_db_exists(user_id):
            # First time - create full index
            logger.info(f"Creating initial vector database for user {user_id}")
            
            config = get_pipeline_config(user_id)
            paths = get_user_paths(user_id)
            os.makedirs(os.path.dirname(paths["vector_db_path"]), exist_ok=True)
            
            pipeline = DiaryIndexingPipeline(**config)
            results = pipeline.run_full_pipeline(clear_existing=True)
            
            if results.get('status') == 'completed_successfully':
                # Clear cache to force reload
                if user_id in rag_systems_cache:
                    del rag_systems_cache[user_id]
                
                return {
                    "status": "initial_index_created",
                    "message": f"Created initial vector database for user {user_id}",
                    "documents_processed": results.get('documents_loaded', 0),
                    "chunks_created": results.get('chunks_created', 0)
                }
            else:
                return {
                    "status": "failed",
                    "error": results.get('errors', 'Unknown error')
                }
        else:
            # Incremental update for existing DB
            config = get_pipeline_config(user_id)
            pipeline = DiaryIndexingPipeline(**config)
            
            # Get recent entries (last 3 days to catch new ones)
            from datetime import timedelta
            start_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            results = pipeline.incremental_update(start_date)
            
            if results.get('status') == 'success':
                # Clear cache to force reload
                if user_id in rag_systems_cache:
                    del rag_systems_cache[user_id]
                
                documents_added = results.get('documents_added', 0)
                return {
                    "status": "incremental_update_success",
                    "message": f"Updated vector database for user {user_id}",
                    "documents_added": documents_added
                }
            else:
                # If incremental fails, try full rebuild
                logger.warning(f"Incremental update failed for user {user_id}, trying full rebuild")
                results = pipeline.run_full_pipeline(clear_existing=True)
                
                if results.get('status') == 'completed_successfully':
                    if user_id in rag_systems_cache:
                        del rag_systems_cache[user_id]
                    
                    return {
                        "status": "full_rebuild_success",
                        "message": f"Rebuilt vector database for user {user_id}",
                        "documents_processed": results.get('documents_loaded', 0)
                    }
                else:
                    return {
                        "status": "failed",
                        "error": f"Both incremental and full rebuild failed: {results.get('errors', 'Unknown error')}"
                    }
                
    except Exception as e:
        logger.error(f"Auto-index error for user {user_id}: {e}")
        return {"status": "error", "error": str(e)}

@app.delete("/users/{user_id}/cache")
async def clear_user_cache(user_id: int):
    """Clear RAG system cache for a user."""
    if user_id in rag_systems_cache:
        del rag_systems_cache[user_id]
        logger.info(f"Cleared cache for user {user_id}")
        return {"message": f"Cache cleared for user {user_id}"}
    else:
        return {"message": f"No cache found for user {user_id}"}

@app.delete("/users/{user_id}/vector-db")
async def delete_user_vector_db(user_id: int):
    """Delete vector database for a user."""
    try:
        paths = get_user_paths(user_id)
        
        # Clear cache first
        if user_id in rag_systems_cache:
            del rag_systems_cache[user_id]
        
        # Delete vector database directory
        if os.path.exists(paths["vector_db_path"]):
            import shutil
            shutil.rmtree(paths["vector_db_path"])
            logger.info(f"Deleted vector database for user {user_id}")
            return {"message": f"Vector database deleted for user {user_id}"}
        else:
            return {"message": f"No vector database found for user {user_id}"}
            
    except Exception as e:
        logger.error(f"Error deleting vector database for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_service_stats():
    """Get service statistics."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vector_db_base = os.path.join(base_dir, "VectorDB")
        
        # Get list of existing vector databases
        existing_dbs = []
        if os.path.exists(vector_db_base):
            for item in os.listdir(vector_db_base):
                if item.startswith("user_") and item.endswith("_vector_db"):
                    user_id = int(item.replace("user_", "").replace("_vector_db", ""))
                    doc_count = get_document_count(user_id)
                    existing_dbs.append({
                        "user_id": user_id,
                        "path": os.path.join(vector_db_base, item),
                        "document_count": doc_count
                    })
        
        return {
            "cached_users": list(rag_systems_cache.keys()),
            "total_cached_systems": len(rag_systems_cache),
            "existing_vector_databases": existing_dbs,
            "vector_db_base_path": vector_db_base,
            "service_status": "running"
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Ensure VectorDB directory exists
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vector_db_dir = os.path.join(base_dir, "VectorDB")
    os.makedirs(vector_db_dir, exist_ok=True)
    
    print(f"🚀 Starting RAG Service...")
    print(f"📁 Vector DB base path: {vector_db_dir}")
    print(f"🔑 Google API Key configured: {bool(os.getenv('GOOGLE_API_KEY'))}")
    
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=False)
