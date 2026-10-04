import asyncio
import json

import streamlit as st

from agents.chat_agent import ChatAgent
from database.db import load_profile
from intelligence.agent_router import understand
from intelligence.discovery_service import search_opportunities
from llm.manager import LLMManager
from ui import components as c
from core.session import user_id

EXAMPLES = [
    "Find fully funded AI master's scholarships in Germany",
    "Find AI internships in Europe",
    "Find research positions in computer vision",
    "Find master's programmes in Finland for artificial intelligence",
]
_CONTEXT_KEYS = ("opportunity_type", "roles", "countries", "fields", "study_level", "research_level", "extra_terms")


def _profile():
    try:
        return json.loads(load_profile(user_id()) or "{}")
    except Exception:
        return {}


def _run_discovery(intent, profile):
    results, _diag = search_opportunities(
        intent.get("extra_terms", ""), intent.get("opportunity_type", "Master's"),
        intent.get("roles", []), intent.get("countries", []), intent.get("fields", []),
        profile, intent.get("study_level", "Any"), intent.get("research_level", "Any"),
    )
    return results


def _result_text(results):
    if not results:
        return ("I couldn't find any current, actionable matches after checking the source pages, and I did not pad "
                "the list with unrelated results. Try a broader field or another country.")
    lines = [f"I found **{len(results)}** current opportunit{'y' if len(results) == 1 else 'ies'} after checking the source pages:\n"]
    for i, item in enumerate(results[:20], 1):
        meta = getattr(item, "metadata", {}) or {}
        url = c.usable_url(getattr(item, "application_url", ""), getattr(item, "source_url", ""))
        facts = " • ".join([
            f"Country: {c.display_value(getattr(item, 'country', None), 'See source')}",
            f"Deadline: {c.display_value(getattr(item, 'deadline', None), 'Not stated')}",
            f"Funding: {c.display_value(getattr(item, 'funding', None), 'Not stated')}",
            "✅ Source verified" if meta.get("verification_page_fetched") else "⚠️ Not verified",
        ])
        title = f"[{item.title}]({url})" if url else f"**{item.title}**"
        lines.append(f"{i}. {title} — {getattr(item, 'organization', '') or 'Source'}  \n{facts}")
        reason = meta.get("llm_review_reason")
        if reason:
            lines.append(f"   _{reason}_")
    if len(results) > 20:
        lines.append(f"\n…and {len(results) - 20} more — open the matching page from the top menu to browse all of them.")
    return "\n".join(lines)


def _converse(prompt):
    try:
        reply, _acted = asyncio.run(ChatAgent().respond(prompt))
        return reply
    except Exception:
        return ("I can still run structured searches, but my AI provider is unavailable right now. "
                "Check GEMINI_API_KEY / GROQ_API_KEY / OPENROUTER_API_KEY in your .env file and restart the app.")


def render():
    st.header("🤖 AI Agent")
    st.caption("Ask in plain language. The agent extracts your constraints and runs the same verified discovery engine as the search pages — it never invents opportunities.")
    st.caption(c.llm_status_caption())

    st.session_state.setdefault("agent_context", {})
    st.session_state.setdefault("messages", [])
    queued = st.session_state.pop("agent_queued_prompt", None)

    if not st.session_state["messages"]:
        st.markdown("**Try:**")
        for example in EXAMPLES:
            st.button(example, key=f"ex_{example}", on_click=lambda e=example: st.session_state.update(agent_queued_prompt=e))

    for role, content in st.session_state["messages"]:
        with st.chat_message(role):
            st.markdown(content)

    prompt = st.chat_input("e.g. Find scholarships for international students in Japan") or queued
    if not prompt:
        return

    st.session_state["messages"].append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner("Understanding your request…"):
            intent = asyncio.run(understand(prompt, st.session_state["agent_context"]))
        st.session_state["agent_context"] = {k: intent.get(k) for k in _CONTEXT_KEYS}

        if intent.get("intent") == "discover" and intent.get("opportunity_type") not in (None, "", "All"):
            with st.spinner("Searching sources, verifying source pages and reviewing matches…"):
                try:
                    response = _result_text(_run_discovery(intent, _profile()))
                except Exception as exc:
                    response = f"The search hit a problem ({type(exc).__name__}). Please try again."
        elif intent.get("intent") == "discover":
            response = ("I understand this as an opportunity search, but I need the type to search precisely: "
                        "scholarship, job, internship, master's/admission, or research.")
        else:
            with st.spinner("Thinking…"):
                response = _converse(prompt)
        st.markdown(response)
        st.session_state["messages"].append(("assistant", response))
