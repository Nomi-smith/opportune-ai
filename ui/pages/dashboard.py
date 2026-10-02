import streamlit as st


def render():

    st.header("Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("New Matches", "0")

    with col2:
        st.metric("Saved", "0")

    with col3:
        st.metric("Applications", "0")

    with col4:
        st.metric("Upcoming Deadlines", "0")

    st.divider()

    st.subheader("Welcome to Opportune AI")

    st.write(
        """
        Your personal opportunity and application intelligence agent.

        Start by completing your profile. Once your profile is ready,
        Opportune AI will be able to search for opportunities and
        determine which ones match your background.
        """
    )

    st.info(
        "Next step: complete your profile."
    )