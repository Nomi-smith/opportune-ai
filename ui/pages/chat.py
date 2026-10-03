import asyncio
import streamlit as st
from agents.chat_agent import ChatAgent


def render():
    st.header('💬 Chat with Agent')
    st.caption('With an LLM configured, the agent can answer questions and safely update your profile, skills, documents, and application tracker when you explicitly ask it to.')

    for role, content in st.session_state.messages:
        with st.chat_message(role):
            st.write(content)

    prompt = st.chat_input('Ask about opportunities, CVs, profile, applications, or say “add Python to my profile”.')
    if prompt:
        st.session_state.messages.append(('user', prompt))
        with st.chat_message('user'):
            st.write(prompt)
        with st.chat_message('assistant'):
            response, changed = asyncio.run(ChatAgent().respond(prompt))
            st.write(response)
            if changed:
                st.success('Change applied to your Opportune AI data.')
            st.session_state.messages.append(('assistant', response))
