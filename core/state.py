import streamlit as st

from core.session import ensure_session_user

def initialize_session_state():
    defaults = {
        "search_results": [],
        "current_user_id": 1,
        "messages": [],
        "selected_opportunity": None,
        "discovery_diagnostics": [],
        "discovery_page": 1,
        "tailored_cv_path": None,
        "current_page": "Discover",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    ensure_session_user()   # shared local profile, or a private guest profile on a deployed app
