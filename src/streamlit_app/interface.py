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
# import os 
from streamlit_webrtc import webrtc_streamer
import streamlit as st
import random
import time
from datetime import datetime
from typing import Generator
from streamlit_webrtc import WebRtcMode, webrtc_streamer
from backend.get_post import submit_text_to_database, load_entries_from_database

# ========================================
# HELPER FUNCTIONS
# ========================================


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
            st.header(f"📝 {entry['date']} - {entry['title']}")
            
            # Display entry type indicator (using markdown instead of badge)
            entry_type = entry.get('type', 'Text')
            if entry_type == "Audio File":
                st.markdown("🎵 **Audio Entry**")
            else:
                st.markdown("📄 **Text Entry**")
            
            # Display content with proper spacing
            st.markdown("---")
            st.write(entry['content'])
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
                    # Reset form fields after successful save
                    time.sleep(1)  # Delay to show success message
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