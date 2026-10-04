"""Shared UI helpers: header/brand, top navigation state, and display-cleaning utilities."""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

import streamlit as st

# Top-navigation labels, in display order.
NAV_DASHBOARD = "Discover"   # the landing page: category cards + trusted portals
NAV_SCHOLARSHIPS = "Scholarships"
NAV_JOBS = "Jobs"
NAV_INTERNSHIPS = "Internships"
NAV_ADMISSIONS = "Admissions"
NAV_RESEARCH = "Research"
NAV_CV = "CV & Letters"
NAV_AGENT = "🤖 Agent"
NAV_ITEMS = [NAV_DASHBOARD, NAV_SCHOLARSHIPS, NAV_JOBS, NAV_INTERNSHIPS,
             NAV_ADMISSIONS, NAV_RESEARCH, NAV_CV, NAV_AGENT]


def go_to(page: str) -> None:
    """Navigate from a button. Use as on_click=go_to, args=(page,) so it runs before the next render."""
    st.session_state["nav_pills"] = page
    st.session_state["current_page"] = page


_CSS = """
<style>
:root {--oa-accent:#5B7CFA; --oa-line:rgba(128,128,128,.22); --oa-soft:rgba(91,124,250,.10);}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {display:none !important;}
.block-container {padding-top: 2rem; max-width: 1120px;}
h1, h2, h3, h4 {letter-spacing:-.015em;}
.oa-brand {display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; margin:0 0 .6rem 0;}
.oa-logo {width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center;
          background:linear-gradient(135deg,#5B7CFA,#8B5CF6); color:#fff; font-size:1.05rem;}
.oa-brand .oa-name {font-size:1.35rem; font-weight:700; letter-spacing:-.02em;}
.oa-brand .oa-tag {font-size:.85rem; opacity:.55; padding-left:.7rem; border-left:1px solid var(--oa-line);}
.oa-hero {padding:1.4rem 1.6rem; border-radius:16px; margin:.4rem 0 1.4rem 0; border:1px solid var(--oa-line);
          background:linear-gradient(135deg, var(--oa-soft), rgba(139,92,246,.07));}
.oa-hero h1 {font-size:2rem; margin:0 0 .25rem 0; font-weight:700;}
.oa-hero p {opacity:.72; font-size:1rem; margin:0;}
.oa-icon {width:42px; height:42px; border-radius:11px; display:flex; align-items:center; justify-content:center;
          font-size:1.3rem; background:var(--oa-soft); margin-bottom:.55rem;}
.oa-card-title {font-size:1.05rem; font-weight:650; margin:0 0 .1rem 0;}
.oa-card-sub {opacity:.62; font-size:.88rem; margin-bottom:.7rem; min-height:2.3em;}
.oa-section {font-size:1.15rem; font-weight:650; margin:1.6rem 0 .2rem 0;}
.oa-chip {display:inline-block; font-size:.74rem; font-weight:600; padding:.12rem .55rem; border-radius:999px;
          margin:0 .35rem .3rem 0; border:1px solid var(--oa-line); opacity:.9;}
.oa-chip.ok {background:rgba(34,197,94,.12); border-color:rgba(34,197,94,.35);}
.oa-chip.warn {background:rgba(245,158,11,.12); border-color:rgba(245,158,11,.35);}
.oa-chip.info {background:var(--oa-soft); border-color:rgba(91,124,250,.35);}
.oa-title {font-size:1.12rem; font-weight:650; line-height:1.3; margin:0 0 .15rem 0;}
.oa-org {opacity:.68; font-size:.92rem; margin-bottom:.5rem;}
.oa-fact-l {font-size:.68rem; text-transform:uppercase; letter-spacing:.06em; opacity:.5; margin-bottom:.1rem;}
.oa-fact-v {font-size:.93rem; font-weight:550; overflow-wrap:anywhere;}
.oa-summary {opacity:.8; font-size:.93rem; margin:.4rem 0 .7rem 0; line-height:1.5;}
div[data-testid="stVerticalBlockBorderWrapper"] {border-radius:14px;}
@media (max-width: 640px) {.oa-brand .oa-tag {display:none;} .oa-hero h1 {font-size:1.5rem;} .oa-hero {padding:1rem;}}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def render_brand() -> None:
    st.markdown(
        '<div class="oa-brand"><span class="oa-logo">🎯</span><span class="oa-name">Opportune AI</span>'
        '<span class="oa-tag">Personal opportunity &amp; application intelligence</span></div>',
        unsafe_allow_html=True,
    )


def chip(text: str, kind: str = "") -> str:
    return f'<span class="oa-chip {kind}">{html.escape(str(text))}</span>'


def fact(label: str, value: str) -> str:
    return f'<div class="oa-fact-l">{html.escape(label)}</div><div class="oa-fact-v">{html.escape(str(value))}</div>'


def llm_status_caption() -> str:
    """One-line description of the active LLM chain (no keys are ever shown)."""
    try:
        from llm.manager import LLMManager
        names = [p.name for p in LLMManager().providers if getattr(p, "name", "fallback") != "fallback"]
    except Exception:
        names = []
    if names:
        return "AI providers: " + " → ".join(n.title() for n in names) + " → deterministic fallback"
    return "No external AI provider configured — running in reduced mode (add GEMINI_API_KEY, GROQ_API_KEY or OPENROUTER_API_KEY to .env)."


# ---------------------------------------------------------------- display cleaning
_NOT_STATED = {"", "n/a", "na", "none", "null", "not stated", "unknown", "see source"}


def display_value(value, fallback: str = "Not stated · see source") -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if text.casefold() in _NOT_STATED:
        return fallback
    return text[:160]


_NOISE = re.compile(
    r"(skip to (main )?content|cookie|accept all|privacy policy|terms of use|sign in|log in|log ?out|"
    r"subscribe|newsletter|all rights reserved|©|javascript|enable js|toggle navigation|breadcrumb|share on|"
    r"facebook|twitter|linkedin|whatsapp|pinterest|written by|posted by|\\d+ comments?|min(?:ute)? read|share this)",
    re.I,
)


def clean_summary(text: str, limit: int = 300) -> str:
    """Return a short readable summary, dropping scraped navigation/boilerplate fragments."""
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return ""
    good, total = [], 0
    for part in re.split(r"(?<=[.!?])\s+", text[:5000]):
        part = part.strip()
        words = part.split()
        if len(words) < 7 or len(part) < 40:
            continue
        if _NOISE.search(part) or part.count("|") >= 2 or part.count("•") >= 3 or "»" in part:
            continue
        # Menus scrape as long runs of Capitalised Words with no sentence structure.
        if sum(1 for w in words if w[:1].isupper()) / len(words) > 0.6:
            continue
        good.append(part)
        total += len(part)
        if total >= limit:
            break
    summary = " ".join(good)
    if len(summary) > limit:
        summary = summary[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return summary


_SEARCH_HOST = re.compile(
    r"^(www\.)?(google\.[a-z.]+|bing\.com|duckduckgo\.com|search\.yahoo\.com|search\.brave\.com|"
    r"baidu\.com|yandex\.[a-z.]+|serper\.dev|vertexaisearch\.cloud\.google\.com)$"
)


def is_search_engine_url(url: str) -> bool:
    try:
        host = urlparse(url or "").netloc.lower()
    except Exception:
        return True
    return not host or bool(_SEARCH_HOST.match(host))


def usable_url(*candidates) -> str:
    """First http(s) URL that is a real destination, never a search-engine/redirect URL."""
    for url in candidates:
        url = str(url or "").strip()
        if url.startswith(("http://", "https://")) and not is_search_engine_url(url):
            return url
    return ""
