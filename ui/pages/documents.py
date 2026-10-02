import streamlit as st


def render():

    st.header("Documents")

    st.write(
        "Upload your master CV and application documents."
    )

    uploaded_file = st.file_uploader(
        "Upload document",
        type=[
            "pdf",
            "docx",
            "txt",
        ],
    )

    if uploaded_file:

        st.success(
            f"{uploaded_file.name} uploaded successfully."
        )

        st.info(
            "Document extraction and intelligent analysis "
            "will be added in the document-processing phase."
        )