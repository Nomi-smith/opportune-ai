import streamlit as st

from ui import components as c
from ui.pages import chat, cv_letters, dashboard, discover


def _page_table():
    return {
        c.NAV_DASHBOARD: dashboard.render,
        c.NAV_SCHOLARSHIPS: lambda: discover.render_type("Scholarship"),
        c.NAV_JOBS: lambda: discover.render_type("Job"),
        c.NAV_INTERNSHIPS: lambda: discover.render_type("Internship"),
        c.NAV_ADMISSIONS: lambda: discover.render_type("Master's"),
        c.NAV_RESEARCH: lambda: discover.render_type("Research"),
        c.NAV_CV: cv_letters.render,
        c.NAV_AGENT: chat.render,
    }


def _on_nav_change():
    # st.pills can be deselected (None); keep the current page instead of showing nothing.
    choice = st.session_state.get("nav_pills")
    if choice is None:
        st.session_state["nav_pills"] = st.session_state.get("current_page", c.NAV_DASHBOARD)
    else:
        st.session_state["current_page"] = choice


def render_navigation():
    pages = _page_table()
    st.session_state.setdefault("current_page", c.NAV_DASHBOARD)
    st.session_state.setdefault("nav_pills", st.session_state["current_page"])
    st.pills(
        "Navigate", c.NAV_ITEMS, selection_mode="single", key="nav_pills",
        label_visibility="collapsed", on_change=_on_nav_change,
    )
    page = st.session_state.get("nav_pills") or st.session_state["current_page"]
    st.session_state["current_page"] = page
    st.divider()
    pages.get(page, dashboard.render)()
