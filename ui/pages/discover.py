import streamlit as st


def render():

    st.header("Discover Opportunities")

    opportunity_type = st.selectbox(
        "Opportunity type",
        [
            "All",
            "Jobs",
            "Internships",
            "Master's",
            "Scholarships",
            "Research",
        ],
    )

    query = st.text_input(
        "What are you looking for?",
        placeholder="e.g. Fully funded AI master's in Europe",
    )

    country = st.text_input(
        "Preferred country",
        placeholder="e.g. Germany",
    )

    if st.button("Search Opportunities"):

        if not query:
            st.warning(
                "Please enter what you're looking for."
            )
            return

        st.info(
            "Opportunity discovery will be connected "
            "in the next development phase."
        )

        st.session_state.search_results = []