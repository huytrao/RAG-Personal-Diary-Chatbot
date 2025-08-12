import streamlit as st

def init_session_state():
    if "diary_entries" not in st.session_state:
        st.session_state.diary_entries = []
    if "show_form" not in st.session_state:
        st.session_state.show_form = False

def add_entry_form():
    st.header("Add New Diary Entry")

    date = st.date_input("Date")
    title = st.text_input("Title")
    entry_type = st.radio("Entry type", options=["Text", "Audio File"])

    content = None
    if entry_type == "Text":
        content = st.text_area("Write your diary entry here")
    else:
        audio_file = st.file_uploader("Upload an audio file", type=["mp3", "wav", "ogg"])
        if audio_file:
            content = audio_file

    if st.button("Save Entry"):
        if not title:
            st.warning("Please enter a title")
        elif not content:
            st.warning("Please provide diary content (text or audio file)")
        else:
            st.session_state.diary_entries.append({
                "date": date.strftime("%Y-%m-%d"),
                "title": title,
                "type": entry_type,
                "content": content
            })
            st.success("Diary entry added!")
            st.session_state.show_form = False

def show_diary_list():
    st.sidebar.header("Diary List")
    if st.session_state.diary_entries:
        selected = st.sidebar.radio(
            "Select Entry",
            options=[f"{d['date']} - {d['title']}" for d in st.session_state.diary_entries]
        )
        for d in st.session_state.diary_entries:
            if f"{d['date']} - {d['title']}" == selected:
                st.sidebar.markdown(f"### {d['date']} - {d['title']}")
                if d["type"] == "Text":
                    st.sidebar.write(d["content"])
                else:
                    st.sidebar.audio(d["content"])
    else:
        st.sidebar.write("No diary entries yet.")

