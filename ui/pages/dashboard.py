import streamlit as st
from database.db import list_applications, list_documents

def render():
    st.header("📊 Dashboard")
    applications = list_applications(1)
    documents = list_documents(1)

    col1, col2 = st.columns(2)
    col1.metric("Tracked applications", len(applications))
    col2.metric("Saved documents", len(documents))

    st.info(
        "Use Discover to find opportunities, Profile to provide your background, "
        "Documents to upload your master CV, and Applications to track progress."
    )
