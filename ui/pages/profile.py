import streamlit as st

from models.user import Education, UserProfile


def render():

    st.header("My Profile")

    name = st.text_input(
        "Name",
        value=st.session_state.user_profile.get(
            "name",
            "",
        ),
    )

    email = st.text_input(
        "Email",
        value=st.session_state.user_profile.get(
            "email",
            "",
        ),
    )

    st.subheader("Education")

    degree = st.text_input(
        "Degree",
        placeholder="e.g. BS Computer Science",
    )

    field = st.text_input(
        "Field",
        placeholder="e.g. Artificial Intelligence",
    )

    institution = st.text_input(
        "Institution",
        placeholder="e.g. Abdul Wali Khan University",
    )

    cgpa = st.number_input(
        "CGPA",
        min_value=0.0,
        max_value=4.0,
        value=0.0,
        step=0.01,
    )

    graduation_date = st.text_input(
        "Expected graduation date",
        placeholder="e.g. October 2026",
    )

    skills = st.text_area(
        "Skills",
        placeholder="Python, Machine Learning, Computer Vision...",
    )

    interests = st.text_area(
        "Career interests",
        placeholder="Generative AI, ML, AI Agents...",
    )

    countries = st.text_input(
        "Preferred countries",
        placeholder="Germany, Netherlands, Sweden",
    )

    if st.button("Save Profile"):

        education = Education(
            degree=degree,
            institution=institution,
            field=field,
            cgpa=cgpa if cgpa > 0 else None,
            graduation_date=graduation_date,
        )

        profile = UserProfile(
            name=name,
            email=email,
            education=[education],
            skills=[
                item.strip()
                for item in skills.split(",")
                if item.strip()
            ],
            career_interests=[
                item.strip()
                for item in interests.split(",")
                if item.strip()
            ],
            preferred_countries=[
                item.strip()
                for item in countries.split(",")
                if item.strip()
            ],
        )

        st.session_state.user_profile = profile.model_dump()

        st.success("Profile saved successfully.")