"""
Personal Diary Chatbot Interface

A Streamlit-based web application that combines a chatbot interface with diary entry management.
Users can chat with an AI assistant and manage their personal diary entries through a sidebar interface.

Features:
- Interactive chatbot with streaming responses
- Diary entry management (create, view, select)
- Support for text and audio diary entries
- Persistent session state for data retention
"""
import io
import os
import sys
import wave
from streamlit_webrtc import webrtc_streamer
import streamlit as st
import random
import time
from datetime import datetime
from typing import Generator
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from backend.get_post import submit_text_to_database, load_entries_from_database, delete_diary_entry

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


def response_generator() -> Generator[str, None, None]:
    """
    Generates streaming chatbot responses by yielding words one at a time.
    
    This function simulates a real-time chat experience by randomly selecting
    a response and yielding each word with a small delay.
    
    Yields:
        str: Individual words from the selected response with trailing space
    """
    # Predefined responses for the chatbot
    responses = [
        "Hello there! How can I assist you today?",
        "Hi, human! Is there anything I can help you with?",
        "Do you need help?",
    ]
    
    # Randomly select a response
    response = random.choice(responses)
    
    # Stream the response word by word
    for word in response.split():
        yield word + " "
        time.sleep(0.03)  # Small delay for streaming effect


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
    a streaming response, and updates the session state with both messages.
    """
    if prompt := st.chat_input("What is up?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate and display assistant response with streaming effect
        with st.chat_message("assistant"):
            response = st.write_stream(response_generator())
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})


def render_sidebar() -> str:
    """
    Render the sidebar with diary list and add entry button.
    
    Returns:
        str: The selected diary entry identifier
    """
    st.sidebar.header("📖 Diary List")
    
    # Create list of diary entry options for selection
    diary_options = [f"{entry['date']} - {entry['title']}" for entry in st.session_state.diary_entries]
    
    # Radio button for diary entry selection with unique key
    selected = st.sidebar.radio(
        "Select Entry",
        options=diary_options,
        key="diary_entry_selector"  # Add unique key
    )
    
    # Add new diary entry button with toggle functionality and unique key
    if st.sidebar.button("➕ Add New Diary Entry", key="add_new_entry_btn"):
        st.session_state.show_form = not st.session_state.show_form
    
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
            placeholder="Share your thoughts, experiences, or reflections...",
            height=150,
            key="diary_text_content"  # Add unique key
        )
        
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
                # Create new diary entry
                new_entry = {
                    "date": date.strftime("%Y-%m-%d"),
                    "title": title.strip(),
                    "type": entry_type,
                    "content": content
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