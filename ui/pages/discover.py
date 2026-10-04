import asyncio, hashlib, html, json

import streamlit as st

from agents.application_agent import ApplicationPreparationAgent
from intelligence.agent_intelligence import analyze_opportunity
from intelligence.discovery_planner import (
    COUNTRY_OPTIONS, FIELD_OPTIONS, RESEARCH_LEVELS, ROLE_OPTIONS,
)
from intelligence.discovery_service import search_opportunities  # noqa: F401  (re-exported for callers)
from intelligence.opportunity_intelligence import enhance_opportunity_with_llm, extract_opportunity_details
from intelligence.source_facts import apply_source_facts
from database.db import load_profile
from models.opportunity import Opportunity
from sources.webfetch import fetch_url
from ui import components as c
from core.session import user_id

# planner type -> page presentation
TYPES = {
    "Scholarship": {"label": "Scholarships", "icon": "🎓", "blurb": "Funding, fellowships and grants — checked against the actual source page.", "levels": "study"},
    "Job": {"label": "Jobs", "icon": "💼", "blurb": "Open vacancies with a real application route.", "levels": None},
    "Internship": {"label": "Internships", "icon": "🧑‍💻", "blurb": "Internships, placements and trainee roles.", "levels": None},
    "Master's": {"label": "Admissions", "icon": "🎓", "blurb": "Master's and other study programmes with official admission pages.", "levels": "study"},
    "Research": {"label": "Research", "icon": "🔬", "blurb": "Research positions, funded PhDs, fellowships and labs.", "levels": "research"},
}
_COUNTRIES = [x for x in COUNTRY_OPTIONS if not x.startswith("Other")]
_FIELDS = [x for x in FIELD_OPTIONS if not x.startswith("Other")]


def _key(item):
    raw = str(item.get("id") or item.get("application_url") or item.get("source_url") or ((item.get("title") or "") + "|" + (item.get("organization") or "")))
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def _profile():
    try:
        return json.loads(load_profile(user_id()) or "{}")
    except Exception:
        return {}


# ------------------------------------------------------------------ analysis
def _analyze(item_dict):
    async def run():
        item = Opportunity.model_validate(item_dict)
        url = c.usable_url(item.application_url, item.source_url)
        page = await fetch_url(url, timeout=7, max_chars=36000) if url else ""
        if page:
            item.description = page
            item = extract_opportunity_details(item)
        item = apply_source_facts(item)
        return await enhance_opportunity_with_llm(item)
    return asyncio.run(run())


def _chips(values):
    vals = values if isinstance(values, list) else [values]
    vals = [str(x) for x in vals if str(x).strip() and str(x).lower() != "n/a"]
    st.write(" • ".join(vals[:12]) if vals else "Not stated · see source")


def _prepare_documents(item_dict):
    """Hand the analysed opportunity to CV & Letters as pre-filled opportunity details."""
    item = Opportunity.model_validate(item_dict)
    lines = [item.title, item.organization]
    summary = (item.metadata or {}).get("summary") or c.clean_summary(item.description, 1500)
    if summary:
        lines += ["", summary]
    for label, field in [("Education", "education_requirements"), ("Experience", "experience_requirements"),
                         ("Language", "language_requirements"), ("Tests", "test_requirements"),
                         ("Required documents", "required_documents")]:
        vals = [str(v) for v in (getattr(item, field, []) or []) if str(v).strip().lower() != "n/a"]
        if vals:
            lines.append(f"{label}: " + "; ".join(vals))
    st.session_state["cvl_title"] = item.title or ""
    st.session_state["cvl_org"] = item.organization or ""
    st.session_state["cvl_details"] = "\n".join(x for x in lines if x is not None).strip()
    c.go_to(c.NAV_CV)


def _render_analysis(item, profile):
    st.markdown("### 🧠 Opportunity details")
    summary = (item.metadata or {}).get("summary") or c.clean_summary(item.description, 400)
    if summary:
        st.write(summary)
    a, b, d = st.columns(3)
    a.metric("Deadline", c.display_value(item.deadline, "Not stated"))
    b.metric("Funding", c.display_value(item.funding, "Not stated"))
    d.metric("Verification", item.verification_status or "UNVERIFIED")
    tabs = st.tabs(["Eligibility", "Funding & Application", "Profile Match", "Checklist"])
    with tabs[0]:
        for label, field in [("Education", "education_requirements"), ("Experience", "experience_requirements"),
                             ("Language", "language_requirements"), ("Tests", "test_requirements"),
                             ("Nationality", "nationality_restrictions")]:
            st.markdown(f"**{label}**"); _chips(getattr(item, field, []))
    with tabs[1]:
        for label, value in [("Tuition", item.tuition), ("Funding", item.funding), ("Compensation", item.compensation), ("Application fee", item.application_fee)]:
            st.write(f"**{label}:** {c.display_value(value)}")
        st.write(f"**Required documents:** {', '.join(item.required_documents) if item.required_documents else 'Not stated · see source'}")
        url = c.usable_url(item.application_url, item.source_url)
        if url:
            st.link_button("Open source page ↗", url)
    with tabs[2]:
        if profile:
            analysis = analyze_opportunity(profile, item); m = analysis["matching"]; e = analysis["eligibility"]
            x, y, z = st.columns(3)
            x.metric("Profile match", f"{m.get('score', 0)}/100"); y.metric("Matched skills", len(m.get("matched_skills", []))); z.metric("Missing skills", len(m.get("missing_skills", [])))
            st.write(f"**Eligibility status:** {e.get('status', 'UNKNOWN')}")
            if m.get("matched_skills"): st.write("**Matched:** " + ", ".join(m["matched_skills"]))
            if m.get("missing_skills"): st.write("**Missing:** " + ", ".join(m["missing_skills"]))
            if analysis.get("missing_data"): st.info("Profile data still needed: " + ", ".join(analysis["missing_data"]))
        else:
            st.info("Upload your CV in CV & Letters to calculate a personal match.")
    with tabs[3]:
        for i, step in enumerate(ApplicationPreparationAgent().checklist(item), 1):
            st.write(f"{i}. {step}")
        st.button("✍️ Prepare documents for this opportunity", key="prep_" + _key(item.model_dump()),
                  on_click=_prepare_documents, args=(item.model_dump(),), use_container_width=True)
        st.caption("Applications are always submitted manually by you through the official portal.")


# ------------------------------------------------------------------ search form + results
def _search_form(ctx, otype):
    cfg = TYPES[otype]
    kp = f"{ctx}_{otype}"
    with st.form(f"form_{kp}"):
        c1, c2 = st.columns(2)
        with c1:
            if otype in {"Job", "Internship"}:
                roles = st.multiselect("Role", ROLE_OPTIONS, key=f"{kp}_roles", accept_new_options=True,
                                       placeholder="Choose or type roles — or leave empty for broad discovery")
                fields = []
            else:
                fields = st.multiselect("Field", _FIELDS, key=f"{kp}_fields", accept_new_options=True,
                                        placeholder="Choose or type a field / research area")
                roles = []
        with c2:
            countries = st.multiselect("Country", _COUNTRIES, key=f"{kp}_countries", accept_new_options=True,
                                       placeholder="Leave empty for any country")
        c3, c4 = st.columns(2)
        study_level, research_level = "Any", "Any"
        with c3:
            if cfg["levels"] == "study":
                study_level = st.selectbox("Study level", ["Any", "Bachelor's", "Master's", "PhD"],
                                           index=2 if otype == "Master's" else 0, key=f"{kp}_level")
            elif cfg["levels"] == "research":
                research_level = st.selectbox("Research level", RESEARCH_LEVELS, key=f"{kp}_rlevel")
            else:
                st.caption(" ")
        with c4:
            query = st.text_input("Additional keywords (optional)", key=f"{kp}_query",
                                  placeholder="e.g. computer vision, English-taught, fully funded")
        if cfg["levels"] in {"study", "research"}:
            st.caption("Tip: each field is searched in depth (up to 6). For the broadest results pick up to 3 countries, or leave Country empty to search worldwide.")
        submitted = st.form_submit_button(f"🔍 Search {cfg['label'].lower()}", type="primary", use_container_width=True)
    if not submitted:
        return
    with st.spinner("🌍 Searching sources, then verifying each source page…"):
        try:
            results, diag = search_opportunities(query, otype, roles, countries, fields, _profile(), study_level, research_level)
        except Exception as exc:
            st.error(f"Search failed: {exc}")
            return
    st.session_state[f"res::{otype}"] = [x.model_dump() for x in results]
    st.session_state[f"diag::{otype}"] = diag
    st.session_state[f"page::{otype}"] = 1
    st.session_state["selected_opportunity"] = None
    st.session_state["discovery_diagnostics"] = diag


def _set_page(key, value):
    st.session_state[key] = value


def _posted_text(meta):
    from intelligence.discovery_planner import _days_old
    age = _days_old(meta.get("posted_date"))
    if age is None:
        return ""
    return "Posted today" if age == 0 else (f"Posted {age} day{'s' if age != 1 else ''} ago" if age < 60 else "Posted 2+ months ago")


def _render_card(item, otype, idx=0):
    meta = item.get("metadata", {}) or {}
    k = _key(item)
    url = c.usable_url(item.get("application_url"), item.get("source_url"))
    is_job = otype in {"Job", "Internship"}
    with st.container(border=True):
        # badges
        badges = []
        if meta.get("structured_listing"):
            badges.append(c.chip("Live job listing", "ok"))
        elif meta.get("verification_page_fetched"):
            badges.append(c.chip("Source page verified", "ok"))
        else:
            badges.append(c.chip("Not verified against source", "warn"))
        if meta.get("country_source_priority") == "preferred":
            badges.append(c.chip("Preferred source", "info"))
        elif meta.get("source_tier") in {"official", "preferred"}:
            badges.append(c.chip("Official source", "info"))
        if is_job and _posted_text(meta):
            badges.append(c.chip(_posted_text(meta)))
        if not is_job:
            if meta.get("availability") == "confirmed-open":
                badges.append(c.chip("Open · deadline confirmed", "ok"))
            elif meta.get("availability") == "open-deadline-not-stated":
                badges.append(c.chip("Open · confirm deadline on source", "warn"))
        st.markdown("".join(badges), unsafe_allow_html=True)

        title = item.get("title") or "Untitled opportunity"
        st.markdown(f'<div class="oa-title">{html.escape(title)}</div>', unsafe_allow_html=True)
        place = item.get("city") if is_job else item.get("country")
        parts = [item.get("organization") if item.get("organization") not in {None, "", "Unknown"} else None,
                 place or (item.get("country") if is_job else None)]
        st.markdown(f'<div class="oa-org">{html.escape(" · ".join(x for x in parts if x))}</div>', unsafe_allow_html=True)

        summary = c.clean_summary(meta.get("summary") or item.get("description"), 260)
        if summary:
            st.markdown(f'<div class="oa-summary">{html.escape(summary)}</div>', unsafe_allow_html=True)

        if is_job:
            facts = [("Work mode", c.display_value(item.get("work_mode"), "See posting")),
                     ("Type", c.display_value(meta.get("job_type"), "See posting")),
                     ("Pay", c.display_value(item.get("compensation"), "Not stated")),
                     ("Deadline", c.display_value(item.get("deadline"), "Not stated"))]
        else:
            facts = [("Deadline", c.display_value(item.get("deadline"), "Not stated · check source")),
                     ("Funding", c.display_value(item.get("funding"), "Not stated · check source")),
                     ("Level", c.display_value(meta.get("study_level") or meta.get("detected_level"), "See source"))]
        for col, (label, value) in zip(st.columns(len(facts)), facts):
            col.markdown(c.fact(label, value), unsafe_allow_html=True)
        st.write("")
        x, y = st.columns(2)
        with x:
            if url:
                st.link_button("Apply / open source ↗" if is_job else "Open source ↗", url, use_container_width=True)
        with y:
            if st.button("Analyze & prepare", key=f"analyze_{otype}_{idx}_{k}", use_container_width=True):
                with st.spinner("Fetching and analysing the actual opportunity page…"):
                    analyzed = _analyze(item)
                st.session_state["selected_opportunity"] = analyzed.model_dump()
                st.session_state["selected_for"] = otype


def _render_results(otype):
    results = st.session_state.get(f"res::{otype}")
    if results is None:
        st.info("Choose your filters above and search. Only current, source-verified opportunities are shown.")
        return
    diag = st.session_state.get(f"diag::{otype}") or []
    if not results:
        st.warning("No verified current opportunities found. Try a broader field, another country, or leave the country empty for global discovery.")
    else:
        page_size = 10
        total_pages = max(1, (len(results) + page_size - 1) // page_size)
        pkey = f"page::{otype}"
        page = min(max(st.session_state.get(pkey, 1), 1), total_pages)
        st.success(f"{len(results)} {'job postings' if otype in {'Job', 'Internship'} else 'verified current opportunities'} found • page {page} of {total_pages}")
        for n, item in enumerate(results[(page - 1) * page_size: page * page_size]):
            _render_card(item, otype, (page - 1) * page_size + n)
        selected = st.session_state.get("selected_opportunity")
        if selected and st.session_state.get("selected_for") == otype:
            st.divider()
            _render_analysis(Opportunity.model_validate(selected), _profile())
        if total_pages > 1:
            p1, p2, p3 = st.columns([1, 2, 1])
            p1.button("← Previous", key=f"prev_{otype}", disabled=page <= 1, on_click=_set_page, args=(pkey, page - 1))
            p2.write(f"Page {page} / {total_pages}")
            p3.button("Next →", key=f"next_{otype}", disabled=page >= total_pages, on_click=_set_page, args=(pkey, page + 1))
    if diag:
        with st.expander("Search details (sources used)"):
            for d in diag:
                line = f"**{d['source']}** — {d['results']} candidate(s) from {d.get('calls', 1)} quer{'y' if d.get('calls', 1) == 1 else 'ies'} • {d['elapsed']}s"
                st.write(line + (f" • ⚠️ {d['error']}" if d.get("error") else ""))


def _render_library() -> None:
    """Browse the full scholarship catalogue by country, category and level (no search or API key needed)."""
    import pandas as pd
    from intelligence.scholarship_catalog import catalog_options, filter_catalog, load_catalog

    rows = load_catalog()
    opts = catalog_options(rows)
    st.caption(f"{len(rows)} scholarship sources and programmes across {len(opts['countries'])} countries and regions. "
               "These are official sources to check, not verified live calls. Open a source for its current deadline, "
               "or use the Search tab for verified current opportunities.")
    f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
    query = f1.text_input("Search the library", key="lib_q", placeholder="e.g. DAAD, Chevening, engineering")
    countries = f2.multiselect("Country / region", opts["countries"], key="lib_countries")
    cats = f3.multiselect("Category", opts["categories"], key="lib_cats")
    level = f4.selectbox("Level", ["Any", "Bachelor's", "Master's", "PhD"], key="lib_level")
    found = filter_catalog(rows, query, countries, cats, level)
    st.write(f"**{len(found)}** of {len(rows)} sources")
    if not found:
        st.info("Nothing matches those filters. Remove one to widen the list.")
        return
    df = pd.DataFrame([{
        "Name": r["name"], "Country": r["country"], "Category": r["category"], "Level": r["level"] or "See source",
        "Funding": r["funding"] or "See source", "Open to": r["open_to"] or "See source", "Website": r["website"],
    } for r in found])
    st.dataframe(
        df, hide_index=True, height=560,
        column_config={"Website": st.column_config.LinkColumn("Website", display_text="Open ↗"),
                       "Name": st.column_config.TextColumn("Name", width="large")},
    )


def render_type(otype, ctx="page"):
    cfg = TYPES[otype]
    st.header(f"{cfg['icon']} {cfg['label']}")
    st.caption(cfg["blurb"])
    if otype == "Scholarship":
        search_tab, library_tab = st.tabs(["🔎 Search", "📚 Browse library"])
        with search_tab:
            _search_form(ctx, otype)
            _render_results(otype)
        with library_tab:
            _render_library()
        return
    _search_form(ctx, otype)
    _render_results(otype)
