import streamlit as st
from database.db import list_applications

def render():
    st.header("🗺️ Roadmap")

    rows = list_applications(1)

    if not rows:
        st.info("No applications tracked yet.")
        return

    for row in rows:
        st.write(f"### {row['title']}")
        st.write(f"Status: **{row['status']}**")
        st.write(
            f"Next action: **{row['next_action'] or 'Review requirements'}**"
        )
