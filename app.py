#!/usr/bin/env python3
"""
Start RAG Service for Personal Diary Chatbot
"""
import subprocess
import sys
import os
from pathlib import Path
import time

def check_requirements():
    """Check if required packages are installed."""
    required_packages = ['fastapi', 'uvicorn']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print(f"Install with: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def setup_environment():
    """Setup environment and directories."""
    # Ensure VectorDB directory exists
    vector_db_dir = Path("src/VectorDB")
    vector_db_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Vector DB directory: {vector_db_dir.absolute()}")
    
    # Check for .env file
    env_file = Path("src/Indexingstep/.env")
    if env_file.exists():
        print(f"✅ Environment file found: {env_file}")
    else:
        print(f"⚠️  Environment file not found: {env_file}")
        print("Make sure GOOGLE_API_KEY is set in environment")

def start_service():
    """Start the RAG FastAPI service."""
    if not check_requirements():
        return
    
    setup_environment()
    
    service_file = Path("src/rag_service/main.py")
    
    if not service_file.exists():
        print(f"❌ Service file not found: {service_file}")
        print("Please create the RAG service file first")
        return
    
    print("🚀 Starting RAG Service...")
    print("📍 Service URL: http://0.0.0.0:8001")
    print("📖 API Docs: http://0.0.0.0:8001/docs")
    print("💾 Vector databases will be stored in: src/VectorDB/")
    print("\nPress Ctrl+C to stop the service")
    print("-" * 50)
    
    try:
        # Change to project root directory
        os.chdir(Path(__file__).parent)
        
        # Start the service in the background
        process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "src.rag_service.main:app",
            "--host", "0.0.0.0",
            "--port", "8001",
            "--reload"
        ])
        print(f"🔄 RAG Service running in background (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ Error starting service: {e}")
        return None

def start_streamlit():
    # Start Streamlit UI on port 7860 (default for Spaces)
    os.system("streamlit run src/streamlit_app/interface.py --server.port 7860")

if __name__ == "__main__":
    start_service()
    time.sleep(3)
    start_streamlit()