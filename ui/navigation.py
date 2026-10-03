import streamlit as st

from ui.pages import (
    applications,
    chat,
    dashboard,
    discover,
    documents,
    profile,
    roadmap,
    settings,
)

def render_navigation():
    pages = {
        "Dashboard": dashboard.render,
        "Chat with Agent": chat.render,
        "Discover": discover.render,
        "My Profile": profile.render,
        "Documents": documents.render,
        "Applications": applications.render,
        "Roadmap": roadmap.render,
        "Settings": settings.render,
    }

    choice = st.sidebar.radio("Navigate", list(pages.keys()))
    pages[choice]()
