import streamlit as st


def render():

    st.header("Applications")

    st.write(
        "Track your applications and their current status."
    )

    statuses = [
        "Saved",
        "Interested",
        "Preparing",
        "Applied",
        "Interview",
        "Accepted",
        "Rejected",
        "Closed",
    ]

    status = st.selectbox(
        "Filter by status",
        ["All"] + statuses,
    )

    st.info(
        "Application tracking will be connected "
        "to the database in the next phase."
    )