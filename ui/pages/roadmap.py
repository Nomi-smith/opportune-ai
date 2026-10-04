import streamlit as st
from database.db import list_applications
from core.session import user_id

def render():
    st.header("🗺️ Roadmap")

    rows = list_applications(user_id())

    if not rows:
        st.info("No applications tracked yet.")
        return

    for row in rows:
        st.write(f"### {row['title']}")
        st.write(f"Status: **{row['status']}**")
        st.write(
            f"Next action: **{row['next_action'] or 'Review requirements'}**"
        )
