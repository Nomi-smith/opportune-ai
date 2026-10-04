import streamlit as st

from config.settings import APP_NAME
from core.state import initialize_session_state
from database.db import initialize_database
from ui.components import inject_css, render_brand
from ui.navigation import render_navigation

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main():
    initialize_database()
    initialize_session_state()
    inject_css()
    render_brand()
    render_navigation()


if __name__ == "__main__":
    main()
