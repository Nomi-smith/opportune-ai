import streamlit as st
from config.settings import APP_ENV, APP_VERSION, GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, SERPER_API_KEY
from llm.manager import LLMManager

def render():
    st.header("⚙️ Settings")
    st.write(f"**Version:** {APP_VERSION}")
    st.write(f"**Environment:** {APP_ENV}")

    manager = LLMManager()
    external = [p.name for p in manager.providers if getattr(p, "name", "fallback") != "fallback"]
    if external:
        st.success("LLM enabled: " + ", ".join(external))
        st.caption("LLM-assisted search planning, multilingual normalization, CV understanding, and Agent Chat are available.")
    else:
        st.info("No external LLM key is configured. Opportune will use deterministic discovery and matching.")

    st.write(
        "LLM/search keys are optional. Never store website passwords, "
        "MFA secrets, or CAPTCHA data in Opportune AI."
    )
    search_status = []
    search_status.append("Google grounding key configured" if GEMINI_API_KEY else "Google grounding key missing")
    search_status.append("OpenRouter web search configured" if OPENROUTER_API_KEY else "OpenRouter web search key missing")
    search_status.append("Direct Google-results fallback configured" if SERPER_API_KEY else "Direct Google-results fallback not configured")
    st.info("🌐 Search layer: " + " • ".join(search_status))
    st.caption("Discovery uses independent search providers. A Gemini quota error can fall through to OpenRouter/public-web search instead of returning zero results.")
    st.caption("Configure GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, or optional SERPER_API_KEY in your local .env file, then restart Streamlit.")
