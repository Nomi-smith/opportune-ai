import streamlit as st


def initialize_session_state():
    defaults = {
        "current_page": "Dashboard",
        "user_profile": {},
        "search_results": [],
        "selected_opportunity": None,
        "applications": [],
        "chat_messages": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value