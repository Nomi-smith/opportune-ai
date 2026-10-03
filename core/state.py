import streamlit as st

def initialize_session_state():
    defaults = {
        "search_results": [],
        "current_user_id": 1,
        "messages": [],
        "selected_opportunity": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
