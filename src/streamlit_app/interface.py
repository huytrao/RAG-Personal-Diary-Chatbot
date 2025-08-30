"""
Personal Diary Chatbot Interface - Simplified Version

A streamlined Streamlit-based web application for diary management and AI chat.
"""
import os
import sys
import re
import hashlib
import streamlit as st
import random
import time
import subprocess
from datetime import datetime
from typing import Generator, List
from backend.get_post_v3 import submit_text_to_database, load_entries_from_database, delete_diary_entry
from auth_ui import AuthUI

# Voice Input Dependencies
try:
    from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
    import av
    import numpy as np
    import google.generativeai as genai
    import tempfile
    import threading
    import queue
    import concurrent.futures
    VOICE_AVAILABLE = True
except ImportError as e:
    print(f"Voice input dependencies not available: {e}")
    VOICE_AVAILABLE = False

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path for RAG system import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import RAG client
try:
    from rag_client import RAGServiceClient
    rag_client = RAGServiceClient()
    RAG_AVAILABLE = True
    print("✅ RAG client imported successfully")
except ImportError as e:
    print(f"Warning: RAG client not available: {e}")
    rag_client = None
    RAG_AVAILABLE = False

# ========================================
# VOICE INPUT FUNCTIONS
# ========================================

def get_user_audio_directory(user_id: int) -> str:
    """Get user-specific audio directory path."""
    # Get project root directory (go up from src/streamlit_app/)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    audio_dir = os.path.join(project_root, "user_audio", f"user_{user_id}_audio")
    os.makedirs(audio_dir, exist_ok=True)
    return audio_dir

def transcribe_audio_with_gemini_live(audio_data: bytes, user_id: int) -> str:
    """Transcribe audio using Gemini API."""
    try:
        # Get API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "❌ Google API key not configured"
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Save audio temporarily
        audio_dir = get_user_audio_directory(user_id)
        temp_audio_path = os.path.join(audio_dir, f"temp_audio_{int(time.time())}.wav")
        try:
            with open(temp_audio_path, 'wb') as f:
                f.write(audio_data)
            
            # Upload audio file to Gemini
            audio_file = genai.upload_file(path=temp_audio_path, mime_type="audio/wav")
            
            # Use Gemini model for transcription
            model = genai.GenerativeModel("gemini-2.5-flash-lite")
            prompt = """Convert speech to text. Please transcribe this audio recording accurately.
            
Instructions:
- Listen to the audio and convert the spoken words to text
- Maintain proper grammar and punctuation
- Return only the transcribed text, no additional commentary
- If you cannot understand parts of the audio, indicate with [unclear]

Transcription:"""

            response = model.generate_content([prompt, audio_file])

            if response and response.text:
                # Clean up the uploaded file
                try:
                    genai.delete_file(audio_file.name)
                except Exception:
                    pass

                return response.text.strip()
            else:
                return "❌ No transcription received"
        finally:
            # Clean up temporary file
            if os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except Exception as e:
                    print(f"Warning: Could not delete temp audio file: {e}")
    except PermissionError:
        return "⚠️ Vui lòng cấp quyền truy cập microphone"
    except Exception as e:
        print(f"Transcription error: {e}")
        return f"❌ Transcription failed: {str(e)}"

class AudioProcessor:
    """Audio processor for real-time audio capture."""
    
    def __init__(self):
        self.audio_frames = queue.Queue()
        self.is_recording = False
    
    def audio_frame_callback(self, frame):
        """Callback for processing audio frames."""
        if self.is_recording:
            audio_array = frame.to_ndarray()
            self.audio_frames.put(audio_array)
        return frame
    
    def start_recording(self):
        """Start recording audio."""
        self.is_recording = True
        self.audio_frames = queue.Queue()
    
    def stop_recording(self):
        """Stop recording and return audio data."""
        self.is_recording = False
        
        # Collect all audio frames
        frames = []
        while not self.audio_frames.empty():
            try:
                frame = self.audio_frames.get_nowait()
                frames.append(frame)
            except queue.Empty:
                break
        
        if not frames:
            return None
        
        # Concatenate frames and ensure proper format
        audio_data = np.concatenate(frames, axis=0)
        
        # Ensure audio is mono (single channel)
        if audio_data.ndim > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Normalize audio data to prevent distortion
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8
        
        # Convert to 16-bit PCM format
        audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
        
        return audio_bytes

# ========================================
# HELPER FUNCTIONS
# ========================================

def extract_title_from_content(content: str) -> str:
    """Extract title from content string."""
    if not content:
        return "Untitled"
    lines = content.split('\n')
    for line in lines:
        if line.startswith('Title: '):
            return line[7:].strip()
    return "Untitled"

def extract_content_from_entry(content: str) -> str:
    """Extract actual content from full content string."""
    if not content:
        return ""
    lines = content.split('\n')
    content_start = False
    result_lines = []
    
    for line in lines:
        if line.startswith('Content: '):
            content_start = True
            result_lines.append(line[9:])
        elif content_start:
            result_lines.append(line)
    
    return '\n'.join(result_lines).strip()

def extract_tags_from_content(content: str) -> List[str]:
    """Extract #tags from content string."""
    if not content:
        return []
    tag_pattern = r'#(\w+(?:[_-]\w+)*)'
    matches = re.findall(tag_pattern, content, re.IGNORECASE)
    return list(set([tag.lower() for tag in matches]))

def parse_tags_input(tags_input: str) -> List[str]:
    """Parse comma-separated tags input."""
    if not tags_input:
        return []
    tags = []
    for tag in tags_input.split(','):
        tag = tag.strip()
        if tag.startswith('#'):
            tag = tag[1:]
        if tag:
            tags.append(tag.lower())
    return list(set(tags))

def generate_tag_color(tag: str) -> str:
    """Generate consistent color for a tag."""
    hash_obj = hashlib.md5(tag.encode())
    hash_hex = hash_obj.hexdigest()
    r = max(60, min(200, int(hash_hex[0:2], 16)))
    g = max(60, min(200, int(hash_hex[2:4], 16)))
    b = max(60, min(200, int(hash_hex[4:6], 16)))
    return f"rgb({r}, {g}, {b})"

def render_tags(tags: List[str]) -> str:
    """Render tags as colored HTML badges."""
    if not tags:
        return ""
    tag_html = []
    for tag in tags:
        color = generate_tag_color(tag)
        tag_html.append(f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; margin: 2px; display: inline-block; font-weight: bold;">#{tag}</span>')
    return "".join(tag_html)

def check_rag_service():
    """Check if RAG service is running."""
    if rag_client:
        return rag_client.health_check()
    return False

def check_ai_availability_detailed(user_id: int):
    """Check detailed AI availability status."""
    if not rag_client:
        return {"overall_status": "error", "error": "RAG client not initialized"}
    
    return rag_client.check_ai_availability(user_id)

def fix_ai_availability(user_id: int):
    """Attempt to fix AI availability issues."""
    if not rag_client:
        return {"status": "error", "error": "RAG client not initialized"}
    
    return rag_client.fix_ai_availability(user_id)

def render_ai_status_widget(user_id: int):
    """Render AI status widget with detailed diagnostics and fix options."""
    st.markdown("### 🤖 AI Assistant Status")
    
    status = check_ai_availability_detailed(user_id)
    overall_status = status.get("overall_status", "unknown")
    
    # Overall status display
    if overall_status == "available":
        st.success("✅ AI Assistant is fully available!")
    elif overall_status == "partial":
        st.warning("⚠️ AI Assistant is partially available")
    elif overall_status == "unavailable":
        st.error("❌ AI Assistant is unavailable")
    elif overall_status == "not_configured":
        st.warning("⚠️ AI Assistant needs configuration")
    elif overall_status == "needs_indexing":
        st.info("ℹ️ AI Assistant needs initial indexing")
    elif overall_status == "empty_database":
        st.warning("⚠️ AI Assistant has no documents to search")
    elif overall_status == "checking":
        st.info("🔄 Checking AI Assistant status...")
    elif overall_status == "error":
        error_msg = status.get('error', 'Unknown error')
        st.error(f"❌ AI Assistant error: {error_msg}")
    else:
        st.warning(f"⚠️ Unknown AI status: {overall_status}")
        if 'error' in status:
            st.error(f"Details: {status.get('error', 'No details available')}")

def initialize_rag_system():
    """Initialize RAG system using service."""
    current_user_id = getattr(st.session_state, 'current_user_id', 1)
    
    try:
        if not check_rag_service():
            st.error("❌ RAG service is not running. Please start: `python start_rag_service.py`")
            st.session_state.rag_system_status = "service_unavailable"
            return False
        
        with st.spinner("🤖 Initializing AI Assistant..."):
            # Get user status
            status = rag_client.get_user_status(current_user_id)
            
            if status.get("status") == "not_indexed":
                st.info("🔄 Creating search index from your diary entries...")
                index_result = rag_client.index_user_data(current_user_id, clear_existing=True)
                
                if index_result.get("status") == "success":
                    st.success(f"✅ Indexed {index_result.get('documents_processed', 0)} documents")
                    st.session_state.rag_system_status = "initialized"
                    return True
                else:
                    st.error(f"❌ Indexing failed: {index_result.get('error', 'Unknown error')}")
                    st.session_state.rag_system_status = "error"
                    return False
            
            elif status.get("status") == "ready":
                st.success(f"✅ AI Assistant ready with {status.get('document_count', 0)} documents!")
                st.session_state.rag_system_status = "initialized"
                return True
            
            elif status.get("status") == "error":
                st.error(f"❌ RAG system error: {status.get('error', 'Unknown error')}")
                st.session_state.rag_system_status = "error"
                return False
            
    except Exception as e:
        st.error(f"❌ Cannot initialize AI Assistant: {str(e)}")
        st.session_state.rag_system_status = "error"
        return False

def response_generator(user_query: str) -> Generator[str, None, None]:
    """Generate responses using RAG service."""
    try:
        current_user_id = getattr(st.session_state, 'current_user_id', 1)
        
        if not check_rag_service():
            response = "❌ RAG service is not available. Please start the service first."
        else:
            # Query RAG service
            chat_history = st.session_state.get('messages', [])
            fast_mode = st.session_state.get('fast_mode', False)
            
            result = rag_client.query_rag(
                user_id=current_user_id,
                query=user_query,
                fast_mode=fast_mode,
                chat_history=chat_history
            )
            
            if result.get("status") == "error":
                response = f"❌ Error: {result.get('error', 'Unknown error')}"
            else:
                response = result.get("response", "No response generated")
                # Show processing time in sidebar
                processing_time = result.get("processing_time", 0)
                st.sidebar.success(f"✅ Response time: {processing_time:.2f}s")
        
    except Exception as e:
        response = f"❌ Error: {str(e)}"
    
    # Stream response
    words = response.split()
    delay = 0.01 if st.session_state.get('fast_mode', False) else 0.03
    
    for word in words:
        yield word + " "
        time.sleep(delay)

def run_auto_sync(user_id: int) -> bool:
    """Auto sync using RAG service after saving new entry."""
    try:
        if not check_rag_service():
            st.warning("⚠️ RAG service not available - entry saved but not indexed")
            return False
        
        # Use the new auto-index endpoint
        result = rag_client.auto_index_new_entry(user_id)
        
        status = result.get("status")
        
        if status == "initial_index_created":
            documents_processed = result.get('documents_processed', 0)
            st.success(f"✅ Created search index with {documents_processed} documents!")
            return True
        elif status == "incremental_update_success":
            documents_added = result.get('documents_added', 0)
            if documents_added > 0:
                st.success(f"🔄 Updated search index (+{documents_added} documents)")
            else:
                st.info("ℹ️ Search index is up to date")
            return True
        elif status == "full_rebuild_success":
            documents_processed = result.get('documents_processed', 0)
            st.success(f"🔄 Rebuilt search index with {documents_processed} documents")
            return True
        elif status == "skipped":
            reason = result.get('reason', 'Unknown reason')
            st.info(f"ℹ️ Indexing skipped: {reason}")
            return False
        elif status == "failed":
            error = result.get('error', 'Unknown error')
            st.warning(f"⚠️ Indexing failed: {error}")
            return False
        elif status == "error":
            error = result.get('error', 'Unknown error')
            st.error(f"❌ Indexing error: {error}")
            return False
        else:
            st.warning(f"⚠️ Unknown indexing status: {status}")
            return False
            
    except Exception as e:
        st.error(f"❌ Auto-sync error: {e}")
        return False

def initialize_session_state() -> None:
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "diary_entries" not in st.session_state:
        user_id = getattr(st.session_state, 'current_user_id', 1)
        try:
            st.session_state.diary_entries = load_entries_from_database(user_id)
        except Exception as e:
            st.error(f"Error loading diary entries: {e}")
            st.session_state.diary_entries = []
    
    if "show_form" not in st.session_state:
        st.session_state.show_form = False
    
    if "rag_system" not in st.session_state:
        st.session_state.rag_system = None
        st.session_state.rag_system_status = "not_initialized"
        
        if RAG_AVAILABLE and os.getenv("GOOGLE_API_KEY"):
            st.session_state.rag_system_status = "ready_to_initialize"

def display_chat_history() -> None:
    """Display chat history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def handle_chat_input() -> None:
    """Handle new chat input."""
    if prompt := st.chat_input("Ask me about your diary..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant"):
            response = st.write_stream(response_generator(prompt))
        
        st.session_state.messages.append({"role": "assistant", "content": response})

def handle_entry_action(prompt):
    """Handle entry action prompts - generate full AI response."""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Generate AI response immediately
    try:
        response = ""
        current_user_id = getattr(st.session_state, 'current_user_id', 1)
        
        if not check_rag_service():
            response = "❌ RAG service is not available. Please start the service first."
        else:
            # Query RAG service
            chat_history = st.session_state.get('messages', [])[:-1]  # Exclude the current message
            fast_mode = st.session_state.get('fast_mode', False)
            
            result = rag_client.query_rag(
                user_id=current_user_id,
                query=prompt,
                fast_mode=fast_mode,
                chat_history=chat_history
            )
            
            if result.get("status") == "error":
                response = f"❌ Error: {result.get('error', 'Unknown error')}"
            else:
                response = result.get("response", "No response generated")
        
        # Add AI response to messages
        st.session_state.messages.append({"role": "assistant", "content": response})
        
    except Exception as e:
        response = f"❌ Error generating response: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Close the menu and rerun to show the conversation
    st.session_state.show_entry_actions = False
    st.rerun()

def check_and_sync_entries():
    """Check and sync entries with RAG system."""
    current_user_id = getattr(st.session_state, 'current_user_id', 1)
    
    try:
        if not check_rag_service():
            st.sidebar.error("❌ RAG service offline")
            return
        
        with st.sidebar.spinner("🔄 Checking sync status..."):
            # Get current status
            status = rag_client.get_user_status(current_user_id)
            doc_count = status.get("document_count", 0)
            
            # Count actual diary entries
            actual_count = len(st.session_state.diary_entries)
            
            if doc_count != actual_count:
                st.sidebar.warning(f"⚠️ Sync issue: {doc_count} indexed vs {actual_count} entries")
                
                if st.sidebar.button("🔄 Fix Sync", key="fix_sync_btn"):
                    with st.sidebar.spinner("🔄 Re-syncing..."):
                        result = rag_client.index_user_data(current_user_id, clear_existing=True)
                        if result.get("status") == "success":
                            st.sidebar.success(f"✅ Synced {result.get('documents_processed', 0)} documents")
                        else:
                            st.sidebar.error("❌ Sync failed")
            else:
                st.sidebar.success(f"✅ Sync OK: {doc_count} documents")
                
    except Exception as e:
        st.sidebar.error(f"❌ Sync check error: {str(e)}")

def render_sidebar() -> str:
    """Render sidebar with diary list and controls."""
    st.sidebar.header("📖 Diary List")
    
    # Tag filter
    all_tags = set()
    for entry in st.session_state.diary_entries:
        entry_tags = entry.get('tags', '')
        if entry_tags:
            tags = [tag.strip() for tag in entry_tags.split(',') if tag.strip()]
            all_tags.update(tags)
    
    selected_tag_filter = "All"
    if all_tags:
        selected_tag_filter = st.sidebar.selectbox(
            "Filter by tag:",
            options=["All"] + sorted(list(all_tags)),
            key="tag_filter"
        )
    
    # Filter entries
    filtered_entries = st.session_state.diary_entries
    if selected_tag_filter != "All":
        filtered_entries = [
            entry for entry in st.session_state.diary_entries
            if selected_tag_filter in entry.get('tags', '').split(',')
        ]
    
    st.sidebar.markdown("---")
    
    # Add entry button - Always show this
    if st.sidebar.button("➕ Add New Entry"):
        st.session_state.show_form = not st.session_state.show_form
        st.rerun()
    
    # Show entry list only if there are entries
    if not filtered_entries:
        st.sidebar.warning("No entries found.")
        selected = None
    else:
        # Create entry options
        diary_options = []
        for entry in filtered_entries:
            option_str = f"{entry.get('date', 'Unknown')} - {extract_title_from_content(entry.get('content', ''))}"
            diary_options.append(option_str)
        
        selected = st.sidebar.radio("Select Entry:", options=diary_options)
        
        # Enhanced Entry Actions Menu
        if st.sidebar.button("➕ Entry Actions", key="entry_actions_btn"):
            st.session_state.show_entry_actions = not st.session_state.get('show_entry_actions', False)
            st.rerun()
        
        # Show entry actions menu if toggled
        if st.session_state.get('show_entry_actions', False):
            with st.sidebar.expander("🎯 Smart Actions", expanded=True):
                st.markdown("**Essential AI Functions:**")
                
                # Row 1
                col1, col2 = st.sidebar.columns(2)
                with col1:
                    if st.button("🎯 Extract Key Points", use_container_width=True, key="extract_btn"):
                        handle_entry_action("Summarize and extract the main key points from my diary entries. Focus on important decisions, lessons learned, significant events, and actionable insights.")
                    if st.button("⚡ Next Actions", use_container_width=True, key="next_actions_btn"):
                        handle_entry_action("Suggest concrete next actions and steps I should take based on my historical data, current goals, and diary patterns. What should I focus on this week?")
                    if st.button("🎯 Goal Tracker", use_container_width=True, key="goals_btn"):
                        handle_entry_action("Track my goals and objectives mentioned in diary entries. Analyze progress, identify stuck areas, and suggest ways to accelerate achievement.")
                
                with col2:
                    if st.button("� Get Insights", use_container_width=True, key="insights_btn"):
                        handle_entry_action("Analyze my diary data and provide deep insights about my behavior patterns, productivity cycles, emotional states, and areas for improvement.")
                    if st.button("� Strategy Plan", use_container_width=True, key="strategy_btn"):
                        handle_entry_action("Propose strategic plans and approaches based on the learned patterns from my diary. Help me create actionable strategies for achieving my goals.")
                    if st.button("⏰ Deadline Alert", use_container_width=True, key="deadline_btn"):
                        handle_entry_action("Review my diary for any mentioned deadlines, important dates, or time-sensitive tasks. Create alerts and reminders for upcoming important events.")
                
                # Close menu button
                if st.button("❌ Close Menu", use_container_width=True, key="close_entry_actions"):
                    st.session_state.show_entry_actions = False
                    st.rerun()
    
    # AI Status
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 AI Status")
    
    # Check RAG service status
    service_running = check_rag_service()
    rag_status = st.session_state.get('rag_system_status', 'not_initialized')
    
    if not service_running:
        st.sidebar.error("❌ RAG Service Offline")
        st.sidebar.text("Start with: python start_rag_service.py")
    elif rag_status == "initialized":
        st.sidebar.success("✅ AI Active")
        if rag_client:
            current_user_id = getattr(st.session_state, 'current_user_id', 1)
            status = rag_client.get_user_status(current_user_id)
            if status.get("document_count"):
                st.sidebar.metric("Documents", status.get("document_count", 0))
        
        # Fast mode toggle
        fast_mode = st.sidebar.checkbox(
            "Fast Mode", 
            value=st.session_state.get('fast_mode', False)
        )
        st.session_state.fast_mode = fast_mode
        
    elif rag_status == "ready_to_initialize":
        st.sidebar.info("🔄 AI Ready")
        if st.sidebar.button("🚀 Initialize AI"):
            initialize_rag_system()
            st.rerun()
        
    else:
        st.sidebar.warning("⚠️ AI Unavailable")
        if service_running and st.sidebar.button("🔄 Retry Initialize"):
            st.session_state.rag_system_status = "ready_to_initialize"
            st.rerun()
    
    # Detailed AI Diagnostics
    st.sidebar.markdown("---")
    current_user_id = getattr(st.session_state, 'current_user_id', 1)
    
    with st.sidebar.expander("🔍 Detailed Diagnostics"):
        if service_running and rag_client:
            try:
                status = check_ai_availability_detailed(current_user_id)
                overall_status = status.get("overall_status", "unknown")
                
                if "checks" in status:
                    details = status["checks"]
                    
                    st.markdown("**Core Components:**")
                    # RAG Modules
                    rag_status = details.get("rag_modules", {})
                    if rag_status.get("available"):
                        st.markdown("✅ RAG modules loaded")
                    else:
                        st.markdown("❌ RAG modules: Not available")
                    
                    # Google API Key
                    api_status = details.get("google_api_key", {})
                    if api_status.get("configured"):
                        st.markdown("✅ Google API key configured")
                    else:
                        st.markdown("❌ Google API: Not configured")
                    
                    st.markdown("**User Data:**")
                    # Vector Database
                    vector_status = details.get("vector_database", {})
                    if vector_status.get("exists"):
                        st.markdown("✅ Vector database ready")
                    else:
                        st.markdown("❌ Vector DB: Not found")
                    
                    # Document Count
                    doc_status = details.get("document_count", {})
                    count = doc_status.get("count", 0)
                    if count > 0:
                        st.markdown(f"✅ {count} documents indexed")
                    else:
                        st.markdown("❌ No documents indexed")
                    
                    # Issues and fixes
                    issues = status.get("issues", [])
                    if issues:
                        st.markdown("**Issues Found:**")
                        for issue in issues:
                            st.markdown(f"⚠️ {issue}")
                    
                    fixes = status.get("suggested_fixes", [])
                    if fixes:
                        st.markdown("**Suggested Actions:**")
                        for fix in fixes:
                            st.markdown(f"🔧 {fix}")
                        
                        # Auto-fix button
                        if st.button("🔧 Attempt Auto-Fix", type="primary", key="sidebar_autofix"):
                            with st.spinner("Fixing AI availability issues..."):
                                fix_result = fix_ai_availability(current_user_id)
                                
                                if fix_result.get("status") == "success":
                                    st.success("✅ AI availability issues fixed!")
                                    if fix_result.get("actions_taken"):
                                        st.info("Actions taken: " + ", ".join(fix_result["actions_taken"]))
                                    st.rerun()
                                else:
                                    st.error(f"❌ Fix failed: {fix_result.get('error', 'Unknown error')}")
                else:
                    st.warning("❌ Could not get detailed status")
            except Exception as e:
                st.error(f"❌ Diagnostics error: {str(e)}")
        else:
            st.warning("❌ RAG service not available")
    
    return selected

def display_selected_diary_entry(selected: str) -> None:
    """Display selected diary entry."""
    for entry in st.session_state.diary_entries:
        entry_identifier = f"{entry.get('date', 'Unknown')} - {extract_title_from_content(entry.get('content', ''))}"
        if entry_identifier == selected:
            # Header with delete button
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.header(f"📝 {entry.get('date', 'Unknown')} - {extract_title_from_content(entry.get('content', ''))}")
            
            with col2:
                if st.button("🗑️ Delete", key=f"delete_{entry.get('id')}", type="secondary"):
                    st.session_state.show_delete_confirm = entry.get('id')
                    st.rerun()
            
            # Display tags
            entry_tags = entry.get('tags', '')
            if entry_tags:
                tag_list = [tag.strip() for tag in entry_tags.split(',') if tag.strip()]
                if tag_list:
                    st.markdown("**Tags:**")
                    st.markdown(render_tags(tag_list), unsafe_allow_html=True)
            
            # Display content
            st.markdown("---")
            st.write(extract_content_from_entry(entry.get('content', '')))
            
            # Handle deletion
            if (hasattr(st.session_state, 'show_delete_confirm') and 
                st.session_state.show_delete_confirm == entry.get('id')):
                
                st.markdown("---")
                st.warning("⚠️ **Confirm Deletion**")
                st.write(f"Delete: **{extract_title_from_content(entry.get('content', ''))}**?")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("✅ Yes, Delete", type="primary"):
                        user_id = getattr(st.session_state, 'current_user_id', 1)
                        
                        with st.spinner("🗑️ Deleting entry and rebuilding search index..."):
                            # Step 1: Delete the diary entry from database
                            success = delete_diary_entry(entry.get('id'), user_id)
                            
                            if success:
                                # Step 2: Delete vector database to ensure clean rebuild
                                if rag_client and check_rag_service():
                                    try:
                                        st.info("🔄 Clearing vector database...")
                                        delete_result = rag_client.delete_vector_db(user_id)
                                        
                                        if delete_result.get("status") == "success":
                                            st.info("✅ Vector database cleared successfully")
                                        else:
                                            st.warning(f"⚠️ Vector DB deletion warning: {delete_result.get('error', 'Unknown')}")
                                    
                                    except Exception as e:
                                        st.warning(f"⚠️ Could not clear vector database: {str(e)}")
                                    
                                    # Step 3: Full re-indexing of all remaining documents
                                    st.info("🔄 Rebuilding search index from all remaining entries...")
                                    try:
                                        index_result = rag_client.index_user_data(user_id, clear_existing=True)
                                        
                                        if index_result.get("status") == "success":
                                            docs_count = index_result.get('documents_processed', 0)
                                            st.success(f"✅ Search index rebuilt with {docs_count} documents")
                                        else:
                                            st.warning(f"⚠️ Re-indexing failed: {index_result.get('error', 'Unknown error')}")
                                    
                                    except Exception as e:
                                        st.error(f"❌ Re-indexing error: {str(e)}")
                                else:
                                    st.warning("⚠️ RAG service not available - entry deleted but search index not updated")
                                
                                # Step 4: Refresh UI
                                st.session_state.diary_entries = load_entries_from_database(user_id)
                                del st.session_state.show_delete_confirm
                                st.success("✅ Entry deleted and search index rebuilt!")
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete diary entry")
                
                with col2:
                    if st.button("❌ Cancel"):
                        del st.session_state.show_delete_confirm
                        st.rerun()
            break

def render_diary_entry_form() -> None:
    """Render diary entry form."""
    st.header("✍️ Add New Diary Entry")
    st.markdown("---")
    
    date = st.date_input("📅 Date", value=datetime.now().date())
    title = st.text_input("📌 Title", placeholder="Enter title...")
    audio = st.audio_input("Record your audio")
    # Prevent infinite rerun loop by using a flag
    if audio and not st.session_state.get('voice_transcribed_content') and not st.session_state.get('audio_transcribed_once'):
        os.makedirs("./temp", exist_ok=True)
        with open("./temp/recorded_audio.wav", "wb") as f:
            f.write(audio.getbuffer())
        st.success("Audio recorded and saved successfully!")
        user_id = getattr(st.session_state, 'current_user_id', 1)
        with st.spinner("🔄 Transcribing audio..."):
            transcribed_text = transcribe_audio_with_gemini_live(audio.getbuffer(), user_id)
            if transcribed_text and not transcribed_text.startswith("❌") and not transcribed_text.startswith("⚠️"):
                st.session_state.voice_transcribed_content = transcribed_text
                st.session_state.audio_transcribed_once = True
                st.success("✅ Voice transcribed successfully!")
                st.rerun()
            else:
                st.session_state.audio_transcribed_once = True
                st.error(transcribed_text or "Failed to transcribe audio")
    # Reset the flag if no audio is present
    if not audio and st.session_state.get('audio_transcribed_once'):
        st.session_state.audio_transcribed_once = False
    
    # Content textarea - use transcribed content if available
    content_value = st.session_state.get('voice_transcribed_content', '')
    if not content_value:
        content_value = st.session_state.get('current_content', '')
    
    content = st.text_area(
        "📖 Content",
        value=content_value,
        placeholder="Write your diary entry... Use #tags! Or use voice input above.",
        height=150,
        key="diary_content_input"
    )
    
    # Clear transcribed content after user sees it
    if 'voice_transcribed_content' in st.session_state:
        del st.session_state.voice_transcribed_content
        # Also reset the transcribed_once flag so next audio triggers transcription
        st.session_state.audio_transcribed_once = False
    
    # Tags
    st.markdown("### 🏷️ Tags")
    tags_input = st.text_input(
        "Tags (comma-separated)",
        placeholder="work, travel, family"
    )
    
    # Combine manual and auto tags
    manual_tags = parse_tags_input(tags_input)
    auto_tags = extract_tags_from_content(content) if content else []
    all_tags = list(set(manual_tags + auto_tags))
    
    # Show preview of all tags
    if all_tags:
        st.markdown("**Tags Preview:**")
        st.markdown(render_tags(all_tags), unsafe_allow_html=True)
    
    # Action buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("💾 Save Entry", type="primary"):
            if title and content:
                user_id = getattr(st.session_state, 'current_user_id', 1)
                
                # Format content with title
                formatted_content = f"Title: {title}\nContent: {content}"
                tags_str = ','.join(all_tags) if all_tags else ''
                
                try:
                    # Tạo entry dictionary theo format mà function cần
                    entry = {
                        "date": date.strftime('%Y-%m-%d'),
                        "content": formatted_content,
                        "tags": tags_str
                    }
                    
                    # Call function với đúng format
                    success = submit_text_to_database(entry=entry, user_id=user_id)
                    
                    if success:
                        # Auto-sync after adding
                        run_auto_sync(user_id)
                        
                        # Refresh entries
                        st.session_state.diary_entries = load_entries_from_database(user_id)
                        st.session_state.show_form = False
                        
                        # Clear any remaining voice content
                        if 'voice_transcribed_content' in st.session_state:
                            del st.session_state.voice_transcribed_content
                        
                        st.success("✅ Diary entry saved successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save diary entry.")
                except Exception as e:
                    st.error(f"❌ Error saving entry: {str(e)}")
            else:
                st.warning("⚠️ Please fill in both title and content.")
    
    with col2:
        if st.button("❌ Cancel"):
            st.session_state.show_form = False
            # Clear any voice content
            if 'voice_transcribed_content' in st.session_state:
                del st.session_state.voice_transcribed_content
            st.rerun()

# ========================================
# MAIN APPLICATION
# ========================================
def main() -> None:
    """Main application function."""
    # Initialize authentication
    auth_ui = AuthUI()
    
    # Check if user is authenticated
    if not auth_ui.check_authentication():
        auth_ui.render_auth_page()
        return
    
    # Get current user info
    try:
        current_user_id = auth_ui.get_current_user_id()
        current_username = auth_ui.get_current_username()
        
        if current_user_id is None:
            current_user_id = 1
        if current_username is None:
            current_username = "User"
            
    except Exception as e:
        st.error(f"❌ Error getting user info: {str(e)}")
        current_user_id = 1
        current_username = "User"
    
    # Check if user changed - reset RAG system for data isolation
    if hasattr(st.session_state, 'current_user_id') and st.session_state.current_user_id != current_user_id:
        st.session_state.rag_system = None
        st.session_state.rag_system_status = "ready_to_initialize" if os.getenv("GOOGLE_API_KEY") else "no_api_key"
        st.session_state.messages = []
        st.session_state.diary_entries = []
        st.warning(f"🔄 Switched to user {current_username}. RAG system reset for data isolation.")
    
    st.session_state.current_user_id = current_user_id
    st.session_state.current_username = current_username
    
    # App title
    st.title("🤖 Diary Chat Bot")
    st.markdown(f"*Welcome back, **{current_username}**! Your AI companion for managing diary entries*")
    
    # AI Status Widget
    if check_rag_service():
        render_ai_status_widget(current_user_id)
    else:
        st.error("❌ **RAG Service is offline**")
        st.info("💡 Start the service with: `python start_rag_service.py`")
    
    st.markdown("---")
    
    # Initialize session state
    initialize_session_state()
    
    # Force reload diary entries for current user
    if not st.session_state.diary_entries:
        st.session_state.diary_entries = load_entries_from_database(current_user_id)
    
    # Initialize RAG system if ready
    if st.session_state.get('rag_system_status') == 'ready_to_initialize':
        initialize_rag_system()
    
    # Render sidebar and get selected entry
    auth_ui.render_user_profile()
    selected_entry = render_sidebar()
    
    # Display selected diary entry
    st.markdown("---")
    if st.session_state.diary_entries and selected_entry:
        display_selected_diary_entry(selected_entry)
    elif not st.session_state.diary_entries:
        st.info("📝 No diary entries found. Click '➕ Add New Entry' in the sidebar to get started!")
    else:
        st.info("📖 Select a diary entry from the sidebar to view its content.")
    
    # Chat section
    st.markdown("---")
    st.subheader("💬 Chat with your AI Assistant")
    
    display_chat_history()
    handle_chat_input()
    
    # Diary entry form
    if st.session_state.show_form:
        st.markdown("---")
        render_diary_entry_form()

if __name__ == "__main__":
    main()
