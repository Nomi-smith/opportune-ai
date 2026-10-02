import streamlit as st

from config.settings import APP_ENV, APP_VERSION


def render():

    st.header("Settings")

    st.subheader("Application")

    st.write(
        f"Version: `{APP_VERSION}`"
    )

    st.write(
        f"Environment: `{APP_ENV}`"
    )

    st.subheader("System")

    st.write(
        "Opportune AI is currently running in lightweight "
        "development mode."
    )

    st.warning(
        "API keys should be stored in environment variables "
        "or Streamlit Secrets, never inside source code."
    )