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
    else:
        st.error(f"❌ Unknown status: {status.get('error', 'Unknown error')}")
    
    # Detailed status breakdown
    if "details" in status:
        details = status["details"]
        
        with st.expander("🔍 Detailed Diagnostics", expanded=(overall_status != "available")):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Core Components:**")
                # RAG Modules
                rag_status = details.get("rag_modules", {})
                if rag_status.get("available"):
                    st.markdown("✅ RAG modules loaded")
                else:
                    st.markdown(f"❌ RAG modules: {rag_status.get('error', 'Unknown error')}")
                
                # Google API Key
                api_status = details.get("google_api_key", {})
                if api_status.get("available"):
                    st.markdown("✅ Google API key configured")
                else:
                    st.markdown(f"❌ Google API: {api_status.get('error', 'Not configured')}")
            
            with col2:
                st.markdown("**User Data:**")
                # Vector Database
                vector_status = details.get("vector_database", {})
                if vector_status.get("available"):
                    st.markdown("✅ Vector database ready")
                else:
                    st.markdown(f"❌ Vector DB: {vector_status.get('error', 'Not found')}")
                
                # Document Count
                doc_status = details.get("document_count", {})
                if doc_status.get("available"):
                    count = doc_status.get("count", 0)
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
                if st.button("🔧 Attempt Auto-Fix", type="primary"):
                    with st.spinner("Fixing AI availability issues..."):
                        fix_result = fix_ai_availability(user_id)
                        
                        if fix_result.get("status") == "success":
                            st.success("✅ AI availability issues fixed!")
                            if fix_result.get("actions_taken"):
                                st.info("Actions taken: " + ", ".join(fix_result["actions_taken"]))
                            st.rerun()
                        else:
                            st.error(f"❌ Fix failed: {fix_result.get('error', 'Unknown error')}")

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
                        success = delete_diary_entry(entry.get('id'), user_id)
                        
                        if success:
                            run_auto_sync(user_id)
                            st.session_state.diary_entries = load_entries_from_database(user_id)
                            del st.session_state.show_delete_confirm
                            st.success("✅ Entry deleted!")
                            st.rerun()
                
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
    
    content = st.text_area(
        "📖 Content",
        placeholder="Write your diary entry... Use #tags!",
        height=150
    )
    
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
