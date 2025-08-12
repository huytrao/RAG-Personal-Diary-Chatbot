"""
Personal Diary Chatbot Interface

A Streamlit-based web application that combines a chatbot interface with diary entry management.
Users can chat with an AI assistant and manage their personal diary entries through a sidebar interface.

Features:
- Interactive chatbot with streaming responses
- Diary entry management (create, view, select)
- Support for text and audio diary entries
- Persistent session state for data retention
- Colorful tag system for organizing entries
"""
import io
import os
import sys
import wave
import re
import hashlib
from streamlit_webrtc import webrtc_streamer
import streamlit as st
import random
import time
from datetime import datetime
from typing import Generator, List
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from backend.get_post import submit_text_to_database, load_entries_from_database, delete_diary_entry

# Load environment variables
from dotenv import load_dotenv
load_dotenv()  # Load .env file from root directory

# Add parent directory to path for RAG system import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import RAG system
try:
    from Retrivel_And_Generation.Retrieval_And_Generator import create_rag_system, DiaryRAGSystem
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RAG system not available: {e}")
    RAG_AVAILABLE = False

# ========================================
# TAG HELPER FUNCTIONS
# ========================================

def extract_tags_from_content(content: str) -> List[str]:
    """
    Extract #tags from content string.
    
    Args:
        content: The diary content string
        
    Returns:
        List of tags found (without # symbol)
    """
    if not content:
        return []
    
    # Find all #tags in content (word characters and non-whitespace)
    tag_pattern = r'#(\w+(?:[_-]\w+)*)'
    matches = re.findall(tag_pattern, content, re.IGNORECASE)
    
    # Remove duplicates and return lowercase tags
    return list(set([tag.lower() for tag in matches]))

def parse_tags_input(tags_input: str) -> List[str]:
    """
    Parse comma-separated tags input and clean them.
    
    Args:
        tags_input: Comma-separated string of tags
        
    Returns:
        List of cleaned tags
    """
    if not tags_input:
        return []
    
    # Split by comma and clean each tag
    tags = []
    for tag in tags_input.split(','):
        tag = tag.strip()
        # Remove # if user added it
        if tag.startswith('#'):
            tag = tag[1:]
        # Only add non-empty tags
        if tag:
            tags.append(tag.lower())
    
    return list(set(tags))  # Remove duplicates

def generate_tag_color(tag: str) -> str:
    """
    Generate a consistent color for a tag based on its name.
    
    Args:
        tag: The tag name
        
    Returns:
        CSS color string
    """
    # Use hash to generate consistent colors
    hash_obj = hashlib.md5(tag.encode())
    hash_hex = hash_obj.hexdigest()
    
    # Extract RGB values from hash
    r = int(hash_hex[0:2], 16)
    g = int(hash_hex[2:4], 16)
    b = int(hash_hex[4:6], 16)
    
    # Ensure colors are not too dark or too light
    r = max(60, min(200, r))
    g = max(60, min(200, g))
    b = max(60, min(200, b))
    
    return f"rgb({r}, {g}, {b})"

def render_tags(tags: List[str]) -> str:
    """
    Render tags as colored HTML badges.
    
    Args:
        tags: List of tag names
        
    Returns:
        HTML string for displaying tags
    """
    if not tags:
        return ""
    
    tag_html = []
    for tag in tags:
        color = generate_tag_color(tag)
        # Use simpler inline styles to avoid rendering issues
        tag_html.append(f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin: 2px; display: inline-block; font-weight: bold;">#{tag}</span>')
    
    return "".join(tag_html)

# ========================================
# HELPER FUNCTIONS
# ========================================

def run_incremental_indexing_simple() -> bool:
    """
    Run incremental indexing by calling the indexing script directly.
    This avoids async/event loop issues in Streamlit.
    
    Returns:
        bool: True if indexing was successful, False otherwise
    """
    try:
        import subprocess
        from datetime import datetime, timedelta
        
        # Check if indexing script exists
        script_path = os.path.join(os.path.dirname(__file__), '..', 'Indexingstep', 'run_indexing.py')
        if not os.path.exists(script_path):
            st.warning("⚠️ Indexing script not found. Skipping indexing.")
            return False
        
        # Check for API key
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'Indexingstep', '.env'))
        if not os.getenv("GOOGLE_API_KEY"):
            st.warning("⚠️ Google API key not found. Skipping indexing.")
            return False
        
        with st.spinner("🔄 Updating search index..."):
            # Get the virtual environment python path
            venv_python = os.path.join(
                os.path.dirname(__file__), '..', '..', '.venv', 'Scripts', 'python.exe'
            )
            
            # Use system python if venv not found
            python_cmd = venv_python if os.path.exists(venv_python) else sys.executable
            
            # Run indexing script with incremental mode
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            
            # Prepare command
            cmd = [
                python_cmd,
                script_path,
                "--mode", "incremental",
                "--start-date", start_date,
                "--end-date", end_date
            ]
            
            # Run the command in background
            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(script_path),
                capture_output=True,
                text=True,
                timeout=120,  # 2 minute timeout
                shell=True  # Use shell on Windows
            )
            
            if result.returncode == 0:
                st.success("✅ Search index updated successfully!")
                # Show some output if available
                if "successfully" in result.stdout.lower():
                    return True
                return True
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                st.warning(f"⚠️ Indexing completed with warnings: {error_msg[:100]}...")
                return True  # Still return True as it might have partially worked
                
    except subprocess.TimeoutExpired:
        st.error("❌ Indexing timeout - operation took too long")
        return False
    except Exception as e:
        st.warning(f"⚠️ Could not run automatic indexing: {str(e)}")
        st.info("💡 You can manually run indexing later using the indexing script.")
        return False


def run_incremental_indexing() -> bool:
    """
    Run incremental indexing to update vector database with new entries.
    
    Returns:
        bool: True if indexing was successful, False otherwise
    """
    try:
        # Import here to avoid circular imports and handle missing modules gracefully
        try:
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Indexingstep'))
            from pipeline import DiaryIndexingPipeline
        except ImportError as e:
            st.error(f"❌ Could not import indexing modules: {e}")
            return False
        
        # Load environment config (similar to run_indexing.py)
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'Indexingstep', '.env'))
        
        config = {
            "google_api_key": os.getenv("GOOGLE_API_KEY"),
            "db_path": os.path.join(os.path.dirname(__file__), "backend", "diary.db"),
            "persist_directory": os.path.join(os.path.dirname(__file__), "..", "Indexingstep", "diary_vector_db"),
            "collection_name": "diary_entries",
            "embedding_model": "models/embedding-001",
            "chunk_size": 800,
            "chunk_overlap": 100,
            "batch_size": 50
        }
        
        # Validate API key
        if not config["google_api_key"]:
            st.warning("⚠️ Google API key not found. Skipping indexing.")
            return False
        
        # Run indexing in a separate thread to avoid event loop issues
        import threading
        import concurrent.futures
        
        def run_indexing_task():
            """Function to run indexing in separate thread"""
            try:
                # Initialize pipeline
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
                
                # Run incremental update for recent entries (last 7 days)
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
                
                results = pipeline.incremental_update(
                    start_date=start_date,
                    end_date=end_date
                )
                
                return results
                
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        # Initialize pipeline
        with st.spinner("🔄 Updating search index..."):
            # Use ThreadPoolExecutor to run indexing in separate thread
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_indexing_task)
                try:
                    # Wait for completion with timeout
                    results = future.result(timeout=120)  # 2 minute timeout
                    
                    if results.get("status") in ["completed_successfully", "success"]:
                        st.success("✅ Search index updated successfully!")
                        return True
                    elif results.get("status") == "error":
                        st.error(f"❌ Indexing error: {results.get('error', 'Unknown error')}")
                        return False
                    else:
                        st.warning("⚠️ Indexing completed with warnings.")
                        return True
                        
                except concurrent.futures.TimeoutError:
                    st.error("❌ Indexing timeout - operation took too long")
                    return False
                except Exception as e:
                    st.error(f"❌ Thread execution error: {str(e)}")
                    return False
                
    except Exception as e:
        st.error(f"❌ Error during indexing setup: {str(e)}")
        return False


def remove_from_vector_database(entry_date: str, entry_title: str) -> bool:
    """
    Remove entry from vector database using a simple script approach.
    
    Args:
        entry_date (str): Date of the entry to remove
        entry_title (str): Title of the entry to remove
        
    Returns:
        bool: True if removal was successful, False otherwise
    """
    try:
        # Create a temporary script to handle the deletion
        script_content = f'''
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "Indexingstep"))

from embedding_and_storing import DiaryEmbeddingAndStorage
from dotenv import load_dotenv

# Load environment config
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "Indexingstep", ".env"))

config = {{
    "google_api_key": os.getenv("GOOGLE_API_KEY"),
    "persist_directory": os.path.join(os.path.dirname(__file__), "..", "Indexingstep", "diary_vector_db"),
    "collection_name": "diary_entries",
    "embedding_model": "models/embedding-001"
}}

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
        filter_criteria = {{
            "date": "{entry_date}",
            "title": "{entry_title}"
        }}
        
        success = embedding_storage.delete_documents_by_metadata(filter_criteria)
        print(f"Vector database deletion: {{success}}")
        
    except Exception as e:
        print(f"Error: {{e}}")
        sys.exit(1)
else:
    print("No API key found")
    sys.exit(1)
'''
        
        # Write temporary script
        temp_script_path = os.path.join(os.path.dirname(__file__), 'temp_delete_vector.py')
        with open(temp_script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Run the script
        import subprocess
        
        # Get the virtual environment python path
        venv_python = os.path.join(
            os.path.dirname(__file__), '..', '..', '.venv', 'Scripts', 'python.exe'
        )
        python_cmd = venv_python if os.path.exists(venv_python) else sys.executable
        
        result = subprocess.run(
            [python_cmd, temp_script_path],
            cwd=os.path.dirname(temp_script_path),
            capture_output=True,
            text=True,
            timeout=60,
            shell=True
        )
        
        # Clean up temporary script
        try:
            os.remove(temp_script_path)
        except:
            pass
        
        if result.returncode == 0:
            st.info("🗑️ Entry also removed from search index")
            return True
        else:
            st.warning("⚠️ Could not remove entry from search index")
            return False
            
    except Exception as e:
        st.warning(f"⚠️ Error removing from vector database: {str(e)}")
        return False


def initialize_rag_system():
    """
    Lazy initialization of RAG system when first needed.
    """
    if st.session_state.get("rag_system_status") == "ready_to_initialize":
        try:
            with st.spinner("🤖 Đang khởi tạo AI Assistant..."):
                vector_db_path = "../Indexingstep/diary_vector_db_enhanced"
                google_api_key = os.getenv("GOOGLE_API_KEY")
                
                st.session_state.rag_system = create_rag_system(
                    vector_db_path=vector_db_path,
                    google_api_key=google_api_key
                )
                
                # Check if system is healthy
                status = st.session_state.rag_system.health_check()
                if status.get("vector_store_healthy"):
                    st.success("🤖 AI Assistant được kích hoạt với dữ liệu nhật ký!")
                    st.session_state.rag_system_status = "initialized"
                    return True
                else:
                    st.warning("⚠️ AI Assistant chưa có dữ liệu nhật ký để học.")
                    st.session_state.rag_system = None
                    st.session_state.rag_system_status = "no_data"
                    return False
                    
        except Exception as e:
            st.error(f"❌ Không thể khởi tạo AI Assistant: {str(e)}")
            st.session_state.rag_system = None
            st.session_state.rag_system_status = "error"
            return False
    
    return st.session_state.get("rag_system") is not None


def response_generator(user_query: str) -> Generator[str, None, None]:
    """
    Generates streaming chatbot responses using RAG system or fallback responses.
    
    Args:
        user_query: The user's input message
    
    Yields:
        str: Individual words from the response with trailing space
    """
    try:
        # Try to use RAG system if available
        if RAG_AVAILABLE:
            # Initialize RAG system if needed
            if not st.session_state.get('rag_system') and st.session_state.get('rag_system_status') == 'ready_to_initialize':
                initialize_rag_system()
            
            # Use RAG system if available
            if st.session_state.get('rag_system'):
                # Get chat history for context
                chat_history = st.session_state.get('messages', [])
                
                # Check if fast mode is enabled
                fast_mode = st.session_state.get('fast_mode', False)
                
                if fast_mode:
                    # Use fast response for speed
                    response = st.session_state.rag_system.generate_fast_response(
                        query=user_query
                    )
                else:
                    # Use full contextual response
                    response = st.session_state.rag_system.generate_contextual_response(
                        query=user_query,
                        chat_history=chat_history
                    )
            else:
                # Fallback to predefined responses
                response = get_fallback_response()
        else:
            # Fallback to predefined responses
            response = get_fallback_response()
        
    except Exception as e:
        # Error handling - use simple fallback
        print(f"Error in response generation: {e}")
        response = "Xin lỗi, tôi gặp chút vấn đề. Bạn có thể thử lại được không?"
    
    # Stream the response word by word
    words = response.split()
    fast_mode = st.session_state.get('fast_mode', False)
    
    # Adjust streaming speed based on mode
    delay = 0.01 if fast_mode else 0.03
    
    for word in words:
        yield word + " "
        time.sleep(delay)  # Faster streaming in fast mode


def get_fallback_response() -> str:
    """Get a fallback response when RAG system is not available."""
    responses = [
        "Xin chào! Tôi có thể giúp gì cho bạn về nhật ký của bạn?",
        "Tôi sẽ giúp bạn tìm hiểu và phân tích nhật ký cá nhân. Bạn muốn biết điều gì?",
        "Hãy cho tôi biết bạn đang tìm kiếm thông tin gì trong nhật ký của mình?",
        "Tôi có thể giúp bạn khám phá những kỷ niệm và cảm xúc trong nhật ký. Bạn quan tâm đến điều gì?",
        "Hiện tại tôi đang ở chế độ cơ bản. Hãy kể cho tôi nghe về nhật ký của bạn!"
    ]
    return random.choice(responses)


def initialize_session_state() -> None:
    """
    Initialize all required session state variables.
    
    This function ensures that all necessary session state variables are
    properly initialized when the app starts or refreshes.
    """
    # Initialize chat message history
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Initialize diary entries with sample data
    if "diary_entries" not in st.session_state:
        st.session_state.diary_entries = load_entries_from_database()
    
    # Initialize form visibility state
    if "show_form" not in st.session_state:
        st.session_state.show_form = False
    
    # Initialize RAG system
    if "rag_system" not in st.session_state:
        st.session_state.rag_system = None
        st.session_state.rag_system_status = "not_initialized"
        
        if RAG_AVAILABLE:
            # Don't initialize immediately - do it lazily when first used
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if google_api_key:
                st.session_state.rag_system_status = "ready_to_initialize"
            else:
                st.warning("⚠️ Không tìm thấy Google API key. AI Assistant sẽ sử dụng chế độ cơ bản.")
                st.session_state.rag_system_status = "no_api_key"
        else:
            st.info("💡 AI Assistant chưa được cấu hình. Sử dụng chế độ cơ bản.")
            st.session_state.rag_system_status = "unavailable"


def display_chat_history() -> None:
    """
    Display all previous chat messages from session state.
    
    This function renders the chat history using Streamlit's chat message
    components, maintaining the conversation context across app reruns.
    """
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def handle_chat_input() -> None:
    """
    Handle new chat input from the user.
    
    This function processes user input, displays it in the chat, generates
    a streaming response using RAG system, and updates the session state.
    """
    if prompt := st.chat_input("Hãy hỏi tôi về nhật ký của bạn..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response with streaming effect
        with st.chat_message("assistant"):
            # Pass the user prompt to response_generator
            response = st.write_stream(response_generator(prompt))
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})


def render_sidebar() -> str:
    """
    Render the sidebar with diary list and add entry button.
    
    Returns:
        str: The selected diary entry identifier
    """
    st.sidebar.header("📖 Diary List")
    
    # Add tag filter section first
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏷️ Filter by Tags")
    
    # Get all unique tags from all entries
    all_tags = set()
    for entry in st.session_state.diary_entries:
        entry_tags = entry.get('tags', '')
        if entry_tags:
            tags = [tag.strip() for tag in entry_tags.split(',') if tag.strip()]
            all_tags.update(tags)
    
    selected_tag_filter = "All"
    if all_tags:
        # Show tag filter options
        selected_tag_filter = st.sidebar.selectbox(
            "Filter by tag:",
            options=["All"] + sorted(list(all_tags)),
            key="tag_filter"
        )
    
    # Filter entries based on selected tag
    filtered_entries = []
    if selected_tag_filter == "All":
        filtered_entries = st.session_state.diary_entries
    else:
        for entry in st.session_state.diary_entries:
            entry_tags = entry.get('tags', '')
            if entry_tags and selected_tag_filter in [tag.strip() for tag in entry_tags.split(',')]:
                filtered_entries.append(entry)
    
    st.sidebar.markdown("---")
    
    # Display entries with tags in a clean format
    if not filtered_entries:
        st.sidebar.warning("No entries found with the selected tag.")
        return None
    
    # Create formatted options showing title and tags
    diary_options = []
    for entry in filtered_entries:
        # Get tags for this entry
        entry_tags = entry.get('tags', '')
        tag_list = [tag.strip() for tag in entry_tags.split(',') if tag.strip()] if entry_tags else []
        
        # Create option string with tags visible
        option_str = f"{entry['date']} - {entry['title']}"
        diary_options.append(option_str)
    
    # Radio button for diary entry selection
    selected = st.sidebar.radio(
        "Select Entry:",
        options=diary_options,
        key=f"diary_entry_selector_{selected_tag_filter}"
    )
    
    # Add new diary entry button
    st.sidebar.markdown("---")
    if st.sidebar.button("➕ Add New Diary Entry", key="add_new_entry_btn"):
        st.session_state.show_form = not st.session_state.show_form
    
    # RAG System Status Section
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 AI Assistant Status")
    
    rag_status = st.session_state.get('rag_system_status', 'not_initialized')
    
    if rag_status == "initialized" and st.session_state.get('rag_system'):
        try:
            status = st.session_state.rag_system.health_check()
            
            if status.get("vector_store_healthy"):
                st.sidebar.success("✅ AI Assistant Active")
                doc_count = status.get("document_count", 0)
                st.sidebar.metric("Documents Indexed", doc_count)
                
                # Fast Mode Toggle
                st.sidebar.markdown("**⚡ Performance Settings**")
                fast_mode = st.sidebar.checkbox(
                    "Fast Mode", 
                    value=st.session_state.get('fast_mode', False),
                    help="Enable for faster responses (shorter, more concise answers)"
                )
                st.session_state.fast_mode = fast_mode
                
                if fast_mode:
                    st.sidebar.caption("🚀 Fast responses enabled")
                else:
                    st.sidebar.caption("💭 Full contextual responses")
                    
            else:
                st.sidebar.warning("⚠️ No indexed data")
                st.sidebar.info("Run indexing to enable AI features")
                
        except Exception as e:
            st.sidebar.error("❌ AI Assistant Error")
            st.sidebar.caption(f"Error: {str(e)}")
    
    elif rag_status == "ready_to_initialize":
        st.sidebar.info("🔄 AI Ready to Initialize")
        st.sidebar.caption("Will initialize on first use")
        
    elif rag_status == "no_api_key":
        st.sidebar.warning("⚠️ No API Key")
        st.sidebar.caption("Set GOOGLE_API_KEY to enable AI")
        
    elif rag_status == "no_data":
        st.sidebar.warning("⚠️ No Data Available")
        st.sidebar.caption("Run indexing to add diary data")
        
    elif rag_status == "error":
        st.sidebar.error("❌ AI Assistant Error")
        st.sidebar.caption("Check logs for details")
        
    else:
        st.sidebar.info("💡 AI Assistant Disabled")
        st.sidebar.caption("Basic responses only")
    
    return selected


def display_selected_diary_entry(selected: str) -> None:
    """
    Display the content of the selected diary entry in the main area.
    
    Args:
        selected (str): The selected diary entry identifier in format "date - title"
    """
    # Find and display the selected diary entry
    for entry in st.session_state.diary_entries:
        entry_identifier = f"{entry['date']} - {entry['title']}"
        if entry_identifier == selected:
            # Header with title and delete button
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.header(f"📝 {entry['date']} - {entry['title']}")
            
            with col2:
                if st.button("🗑️ Delete", key=f"delete_entry_{entry.get('id', entry['date'])}", 
                            help="Delete this diary entry", type="secondary"):
                    # Show confirmation dialog
                    st.session_state.show_delete_confirm = entry.get('id')
                    st.session_state.delete_entry_info = entry
                    st.rerun()
            
            # Display entry type indicator (using markdown instead of badge)
            entry_type = entry.get('type', 'Text')
            if entry_type == "Audio File":
                st.markdown("🎵 **Audio Entry**")
            else:
                st.markdown("📄 **Text Entry**")
            
            # Display tags if they exist
            entry_tags = entry.get('tags', '')
            if entry_tags:
                tag_list = [tag.strip() for tag in entry_tags.split(',') if tag.strip()]
                if tag_list:
                    st.markdown("**Tags:**")
                    st.markdown(render_tags(tag_list), unsafe_allow_html=True)
            
            # Display content with proper spacing
            st.markdown("---")
            st.write(entry['content'])
            
            # Handle delete confirmation dialog
            if hasattr(st.session_state, 'show_delete_confirm') and \
               st.session_state.show_delete_confirm == entry.get('id'):
                
                st.markdown("---")
                st.warning("⚠️ **Confirm Deletion**")
                st.write(f"Are you sure you want to delete the entry: **{entry['title']}** from {entry['date']}?")
                st.write("This action cannot be undone.")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    if st.button("✅ Yes, Delete", type="primary", key="confirm_delete"):
                        # Perform deletion
                        entry_id = entry.get('id')
                        if entry_id:
                            with st.spinner("Deleting entry..."):
                                success = delete_diary_entry(entry_id)
                            
                            if success:
                                # Also remove from vector database
                                with st.spinner("Removing from search index..."):
                                    remove_from_vector_database(entry['date'], entry['title'])
                                
                                # Reload entries from database
                                st.session_state.diary_entries = load_entries_from_database()
                                # Clear confirmation state
                                if hasattr(st.session_state, 'show_delete_confirm'):
                                    del st.session_state.show_delete_confirm
                                if hasattr(st.session_state, 'delete_entry_info'):
                                    del st.session_state.delete_entry_info
                                st.success("✅ Entry deleted successfully from both database and search index!")
                                time.sleep(2)
                                st.rerun()
                        else:
                            st.error("❌ Cannot delete entry: ID not found")
                
                with col2:
                    if st.button("❌ Cancel", key="cancel_delete"):
                        # Clear confirmation state
                        if hasattr(st.session_state, 'show_delete_confirm'):
                            del st.session_state.show_delete_confirm
                        if hasattr(st.session_state, 'delete_entry_info'):
                            del st.session_state.delete_entry_info
                        st.rerun()
            
            break


def render_diary_entry_form() -> None:
    """
    Render the diary entry form for adding new entries.
    """
    st.header("✍️ Add New Diary Entry")
    st.markdown("---")
    
    # Date input with default to today
    date = st.date_input("📅 Date", value=datetime.now().date(), key="diary_date_input")
    
    # Title input with placeholder
    title = st.text_input("📌 Title", placeholder="Enter a descriptive title...", key="diary_title_input")
    
    # Entry type selection
    entry_type = st.radio(
        "📝 Entry Type", 
        options=["Text", "Audio File"],
        key="diary_entry_type_radio"  # Add unique key
    )
    
    # Content input based on selected type
    content = None
    if entry_type == "Text":
        content = st.text_area(
            "📖 Write your diary entry here",
            placeholder="Share your thoughts, experiences, or reflections... You can also use #tags in your content!",
            height=150,
            key="diary_text_content"  # Add unique key
        )
        
        # Tags input section
        st.markdown("### 🏷️ Tags")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            tags_input = st.text_input(
                "Add tags (comma-separated)",
                placeholder="work, travel, family, thoughts, #mood",
                key="diary_tags_input",
                help="Enter tags separated by commas. You can use # or not - we'll handle it!"
            )
        
        with col2:
            if content:
                # Auto-extract tags from content
                auto_tags = extract_tags_from_content(content)
                if auto_tags:
                    st.write("**Found in text:**")
                    for tag in auto_tags:
                        st.markdown(f"#{tag}", unsafe_allow_html=True)
        
        # Parse and combine tags
        manual_tags = parse_tags_input(tags_input)
        auto_tags = extract_tags_from_content(content) if content else []
        all_tags = list(set(manual_tags + auto_tags))  # Combine and remove duplicates
        
        # Show preview of all tags
        if all_tags:
            st.markdown("**Tag Preview:**")
            st.markdown(render_tags(all_tags), unsafe_allow_html=True)
        
    else:
        audio_file = st.file_uploader(
            "🎵 Upload an audio file", 
            type=["mp3", "wav", "ogg", "m4a"],
            key="diary_audio_uploader"  # Add unique key
        )
        st.markdown("🔊 **Audio Entry**")
        voice_record = webrtc_streamer(
            key="voice_record_diary", 
            mode=WebRtcMode.SENDRECV, 
            audio_receiver_size=256, 
            media_stream_constraints={"audio": True, "video": False}, 
            async_processing=True
        )

        if voice_record.audio_receiver:
            frames = voice_record.audio_receiver.get_frames(timeout=1)
            if frames:
                audio_frame = frames[0]
                audio_np = audio_frame.to_ndarray()

                with io.BytesIO() as wav_io:
                    with wave.open(wav_io, "wb") as wav_file:
                        wav_file.setnchannels(audio_frame.layout.channels)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(audio_frame.sample_rate)
                        wav_file.writeframes(audio_np.tobytes())
                    wav_bytes = wav_io.getvalue()

                st.audio(wav_bytes, format="audio/wav")
                
        if audio_file:
            content = f"Audio file: {audio_file.name}"
            st.audio(audio_file)
        
        # For audio entries, still allow tag input
        if entry_type == "Audio File":
            st.markdown("### 🏷️ Tags")
            tags_input = st.text_input(
                "Add tags (comma-separated)",
                placeholder="work, travel, family, thoughts",
                key="diary_audio_tags_input",
                help="Enter tags separated by commas"
            )
            all_tags = parse_tags_input(tags_input)
            
            # Show preview of tags
            if all_tags:
                st.markdown("**Tag Preview:**")
                st.markdown(render_tags(all_tags), unsafe_allow_html=True)
    
    # Action buttons in columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Save Entry", type="primary", key="save_diary_entry_btn"):
            # Input validation
            if not title.strip():
                st.error("❌ Please enter a title for your diary entry.")
            elif not content:
                st.error("❌ Please provide diary content (text or audio file).")
            else:
                # Get tags based on entry type
                if entry_type == "Text":
                    # For text entries, combine manual and auto-extracted tags
                    manual_tags = parse_tags_input(tags_input) if 'tags_input' in locals() else []
                    auto_tags = extract_tags_from_content(content) if content else []
                    final_tags = list(set(manual_tags + auto_tags))
                else:
                    # For audio entries, only manual tags
                    final_tags = parse_tags_input(tags_input) if 'tags_input' in locals() else []
                
                # Create new diary entry
                new_entry = {
                    "date": date.strftime("%Y-%m-%d"),
                    "title": title.strip(),
                    "type": entry_type,
                    "content": content,
                    "tags": ",".join(final_tags)  # Add tags to entry
                }
                
                # Submit to database
                with st.spinner("Saving to database..."):
                    success = submit_text_to_database(new_entry)
                
                if success:
                    # Reload entries from database
                    st.session_state.diary_entries = load_entries_from_database()
                    st.success("✅ Diary entry added successfully!")
                    
                    # Run incremental indexing to update search index (simple version)
                    indexing_success = run_incremental_indexing_simple()
                    if indexing_success:
                        st.info("🔍 Search index updated - your new entry is now searchable!")
                    
                    # Reset form fields after successful save
                    time.sleep(2)  # Longer delay to show success and indexing messages
                    st.session_state.show_form = False
                    st.rerun()
                else:
                    st.error("❌ Failed to add diary entry.")
    
    with col2:
        if st.button("❌ Cancel", key="cancel_diary_entry_btn"):
            st.session_state.show_form = False
            st.rerun()


# ========================================
# MAIN APPLICATION
# ========================================
def main() -> None:
    """
    Main application function that orchestrates the entire app.
    This function sets up the page configuration, initializes the session state,
    and renders all UI components in the correct order.
    """
    # App title and description
    st.title("🤖 Diary Chat Bot")
    st.markdown("*Your AI companion for managing diary entries and conversations*")
    
    # Initialize session state
    initialize_session_state()
    
    # Display chat messages from history on app rerun
    display_chat_history()
    
    # Accept user input for chat
    handle_chat_input()
    
    # Render sidebar and get selected diary entry
    selected_entry = render_sidebar()
    
    # Display selected diary entry in main area
    if st.session_state.diary_entries:
        st.markdown("---")
        display_selected_diary_entry(selected_entry)
    
    # Conditionally render diary entry form
    if st.session_state.show_form:
        st.markdown("---")
        render_diary_entry_form()


# ========================================
# APPLICATION ENTRY POINT
# ========================================

if __name__ == "__main__":
    main()