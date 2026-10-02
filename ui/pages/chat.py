import streamlit as st

from llm.manager import LLMManager


def render():

    st.header("Chat with Agent")

    st.write(
        "Ask Opportune AI about jobs, internships, "
        "scholarships, master's programs, or research."
    )

    for message in st.session_state.chat_messages:

        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input(
        "What opportunity are you looking for?"
    )

    if prompt:

        st.session_state.chat_messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        manager = LLMManager()

        response = manager.generate(prompt)

        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": response,
            }
        )

        st.rerun()