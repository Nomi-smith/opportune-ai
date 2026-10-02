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


PAGES = {
    "Dashboard": dashboard.render,
    "Chat with Agent": chat.render,
    "Discover": discover.render,
    "My Profile": profile.render,
    "Documents": documents.render,
    "Applications": applications.render,
    "Roadmap": roadmap.render,
    "Settings": settings.render,
}


def render_navigation():

    page_names = list(PAGES.keys())

    selected_page = st.sidebar.radio(
        "Navigation",
        page_names,
        index=page_names.index(
            st.session_state.current_page
        ),
    )

    st.session_state.current_page = selected_page

    PAGES[selected_page]()