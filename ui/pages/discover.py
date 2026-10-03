import re
import asyncio
import streamlit as st

from agents.opportunity_agent import OpportunityAgent
from intelligence.agent_intelligence import analyze_opportunity
from intelligence.opportunity_intelligence import extract_opportunity_details, enhance_opportunity_with_llm
from intelligence.discovery_planner import DiscoveryPlanner, ROLE_OPTIONS, COUNTRY_OPTIONS, FIELD_OPTIONS
from database.db import save_application, list_applications
from sources.jobs.arbeitnow import ArbeitnowSource
from sources.research.openalex import OpenAlexSource
from sources.web import PublicWebSource
from sources.openrouter_search import OpenRouterWebSearchSource
from sources.gemini_google_search import GeminiGoogleSearchSource
from sources.serper import SerperGoogleSource
from sources.manager import SourceManager


def _manager():
    return SourceManager([
        GeminiGoogleSearchSource(),
        OpenRouterWebSearchSource(),
        SerperGoogleSource(),
        ArbeitnowSource(),
        OpenAlexSource(),
        PublicWebSource(),
    ])


def search_opportunities(query, opportunity_type=None, roles=None, countries=None, fields=None, profile=None):
    async def run():
        manager = _manager()
        planner = DiscoveryPlanner(manager)
        plan = planner.build_plan(
            opportunity_type or "All",
            roles=roles or [],
            countries=countries or [],
            fields=fields or [],
            query=query,
            profile=profile or {},
        )
        results = await planner.run(plan)
        results = [extract_opportunity_details(x) for x in results]
        # LLM enhancement is optional and only runs when Gemini/Groq/OpenRouter is configured.
        # Keep the first page responsive by enhancing at most 10 results per search.
        enhanced = []
        for index, item in enumerate(results):
            if index < 10:
                item = await enhance_opportunity_with_llm(item)
            enhanced.append(item)
        return enhanced, manager.diagnostics

    return asyncio.run(run())


def _item_key(item):
    import hashlib
    raw = str(item.get("id") or item.get("application_url") or item.get("source_url") or ((item.get("title") or "") + "|" + (item.get("organization") or "")))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _value(value):
    if isinstance(value, list):
        return ", ".join(str(x) for x in value) if value else "N/A"
    return str(value).strip() if value else "N/A"


def _items(values):
    if not values:
        return ["N/A"]
    if isinstance(values, str):
        return [values]
    return values


def _chips(values):
    vals = [str(x) for x in _items(values) if str(x).strip()]
    if not vals:
        vals = ["N/A"]
    st.markdown(
        " ".join(
            f'<span class="op-chip">{v}</span>' for v in vals[:12]
        ),
        unsafe_allow_html=True,
    )


def _section(title, values):
    st.markdown(f"#### {title}")
    vals = _items(values)
    for value in vals[:12]:
        st.markdown(f"- {value}")


def _apply_css():
    st.markdown(
        """
        <style>
        .opp-card {
            padding: 1.1rem 1.2rem;
            border: 1px solid rgba(128,128,128,.22);
            border-radius: 16px;
            margin: .6rem 0 1rem 0;
        }
        .opp-meta {
            color: rgba(128,128,128,.95);
            font-size: .92rem;
            margin-bottom: .6rem;
        }
        .op-chip {
            display:inline-block;
            padding:.28rem .62rem;
            margin:.16rem .16rem .16rem 0;
            border-radius:999px;
            background:rgba(99,102,241,.10);
            border:1px solid rgba(99,102,241,.18);
            font-size:.84rem;
        }
        .na {
            color: rgba(128,128,128,.85);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_match(item, profile):
    if not profile:
        st.info("Add your profile to calculate your personal match.")
        return

    analysis = analyze_opportunity(profile, type("OpportunityObj", (), item)())
    matching = analysis["matching"]
    eligibility = analysis["eligibility"]

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Profile match", f"{matching.get('score', 0)}/100")
    with c2:
        st.metric("Matched skills", len(matching.get("matched_skills", [])))
    with c3:
        st.metric("Missing skills", len(matching.get("missing_skills", [])))

    status = eligibility.get("status", "UNKNOWN")
    st.write(f"**Eligibility:** {status}")

    if matching.get("matched_skills"):
        st.markdown("**Matched skills**")
        _chips(matching["matched_skills"])

    if matching.get("missing_skills"):
        st.markdown("**Missing skills**")
        _chips(matching["missing_skills"])

    missing = analysis.get("missing_data", [])
    if missing:
        st.caption("Profile information still needed: " + ", ".join(missing))


def render():
    _apply_css()

    st.header("🔎 Discover Opportunities")
    st.caption(
        "Find opportunities, inspect structured requirements, compare them with your profile, "
        "and keep N/A when the available source does not state a value."
    )

    if "discovery_page" not in st.session_state:
        st.session_state.discovery_page = 1

    opportunity_type = st.selectbox(
        "Type",
        ["All", "Job", "Internship", "Master's", "Scholarship", "Research"],
    )

    profile = st.session_state.get("profile", {})

    if opportunity_type in {"Job", "Internship"}:
        c1, c2 = st.columns(2)
        with c1:
            roles = st.multiselect(
                "Roles (choose one or more)",
                ROLE_OPTIONS,
                placeholder="Select multiple roles...",
            )
            custom_roles = st.text_input(
                "Custom roles (optional, comma-separated)",
                placeholder="e.g. AI Automation Intern, Agentic AI Intern",
            )
        with c2:
            countries = st.multiselect(
                "Countries (choose one or more)",
                COUNTRY_OPTIONS,
                placeholder="Select multiple countries...",
            )
            custom_countries = st.text_input(
                "Other countries (optional, comma-separated)",
                placeholder="e.g. Estonia, UAE",
            )
        query = st.text_input(
            "Extra keywords (optional)",
            placeholder="e.g. YOLO, LLM, Python",
        )
        fields = []
    elif opportunity_type in {"Master's", "Scholarship", "Research"}:
        c1, c2 = st.columns(2)
        with c1:
            fields = st.multiselect(
                "Fields / research areas (optional)",
                FIELD_OPTIONS,
                placeholder="Leave empty to explore using your profile...",
            )
            query = st.text_input(
                "Extra search terms (optional)",
                placeholder="e.g. computer vision, AI agents",
            )
        with c2:
            countries = st.multiselect(
                "Countries (choose one or more, optional)",
                COUNTRY_OPTIONS,
                placeholder="Select multiple countries...",
            )
            custom_countries = st.text_input(
                "Other countries (optional, comma-separated)",
                placeholder="e.g. Estonia, UAE",
            )
        roles = []
        custom_roles = ""
        st.caption("You do not need to know a program, scholarship, professor, or exact role. Leave the search terms empty and the planner will use your saved profile.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            roles = st.multiselect("Roles (optional)", ROLE_OPTIONS, placeholder="Select multiple roles...")
            custom_roles = st.text_input("Custom roles (optional, comma-separated)")
            query = st.text_input("Keywords (optional)", placeholder="e.g. AI, ML, automation")
        with c2:
            countries = st.multiselect("Countries (optional)", COUNTRY_OPTIONS, placeholder="Select multiple countries...")
            custom_countries = st.text_input("Other countries (optional, comma-separated)")
        fields = st.multiselect("Fields (optional)", FIELD_OPTIONS, placeholder="Select multiple fields...")

    if st.button("🔍 Search Opportunities", type="primary", use_container_width=True):
        import re as _re
        roles = list(roles or []) + [x.strip() for x in _re.split(r"[,\n]", custom_roles or "") if x.strip()]
        countries = list(countries or []) + [x.strip() for x in _re.split(r"[,\n]", custom_countries or "") if x.strip()]

        with st.spinner("Searching multiple sources in parallel..."):
            try:
                results, diagnostics = search_opportunities(
                    query, opportunity_type, roles, countries, fields, profile
                )
                st.session_state.search_results = [x.model_dump() for x in results]
                st.session_state.discovery_diagnostics = diagnostics
                st.session_state.discovery_page = 1
            except Exception as exc:
                st.error(f"Search failed: {exc}")
                return

    results = st.session_state.search_results
    diagnostics = st.session_state.get("discovery_diagnostics", [])
    if diagnostics:
        with st.expander("🛠️ Search diagnostics", expanded=not bool(results)):
            grouped = {}
            for row in diagnostics:
                name = row.get("source", "Unknown")
                grouped.setdefault(name, {"count": 0, "calls": 0, "errors": []})
                grouped[name]["count"] += int(row.get("count") or 0)
                grouped[name]["calls"] += 1
                if row.get("error"):
                    grouped[name]["errors"].append(row["error"])
            for name, info in grouped.items():
                st.write(f"**{name}:** {info['count']} result(s) across {info['calls']} call(s)")
                for err in list(dict.fromkeys(info["errors"]))[:3]:
                    st.caption(err)
    if not results:
        st.info("No results yet.")
        return

    st.divider()
    page_size = 10
    total = len(results)
    total_pages = max(1, (total + page_size - 1) // page_size)
    current_page = min(max(int(st.session_state.get("discovery_page", 1)), 1), total_pages)
    st.session_state.discovery_page = current_page

    st.subheader(f"Found {total} opportunity(s)")
    start_idx = (current_page - 1) * page_size
    end_idx = min(start_idx + page_size, total)
    st.caption(f"Showing {start_idx + 1}–{end_idx} of {total}")

    for item in results[start_idx:end_idx]:
        title = item.get("title") or "Untitled opportunity"
        org = item.get("organization") or "N/A"
        kind = item.get("opportunity_type") or "N/A"
        location = ", ".join(
            x for x in [item.get("city"), item.get("country")] if x
        ) or "N/A"
        verification = item.get("verification_status") or "UNVERIFIED"

        with st.container(border=True):
            st.markdown(f"### {title}")
            st.markdown(
                f'<div class="opp-meta">🏢 {org} &nbsp; • &nbsp; '
                f'💼 {kind} &nbsp; • &nbsp; 📍 {location} &nbsp; • &nbsp; '
                f'🔎 {verification}</div>',
                unsafe_allow_html=True,
            )

            details = item.get("metadata", {}).get("structured_details", {})

            # Only show facts that are actually available. Avoid a wall of N/A values.
            facts = []
            if item.get("compensation_status") not in (None, "", "N/A"):
                facts.append(("Paid", item.get("compensation_status")))
            if item.get("compensation") not in (None, "", "N/A"):
                facts.append(("Compensation", item.get("compensation")))
            if item.get("deadline") not in (None, "", "N/A"):
                facts.append(("Deadline", item.get("deadline")))
            if item.get("work_mode") not in (None, "", "N/A"):
                facts.append(("Work mode", item.get("work_mode")))
            if item.get("duration") not in (None, "", "N/A"):
                facts.append(("Duration", item.get("duration")))

            if facts:
                cols = st.columns(min(4, len(facts)))
                for i, (label, value) in enumerate(facts):
                    with cols[i % len(cols)]:
                        st.caption(label)
                        st.markdown(f"**{value}**")

            tabs = st.tabs(
                ["📋 Overview", "🎓 Requirements", "💰 Money & Conditions",
                 "📝 Application", "👤 Your Match"]
            )

            with tabs[0]:
                st.markdown("#### Quick summary")
                raw_description = item.get("description") or ""
                summary = item.get("metadata", {}).get("summary")

                if not summary:
                    sentences = re.split(r"(?<=[.!?])\\s+", raw_description)
                    sentences = [s.strip() for s in sentences if len(s.strip()) > 25]
                    summary = " ".join(sentences[:3])[:800] if sentences else raw_description[:800]

                st.write(summary or "No description available.")

                if raw_description and len(raw_description) > len(summary or ""):
                    with st.expander("📖 View full description"):
                        st.write(raw_description)

                source_name = item.get("source_name")
                last_verified = item.get("last_verified")
                if source_name or last_verified:
                    source_bits = []
                    if source_name:
                        source_bits.append(f"Source: {source_name}")
                    if last_verified:
                        source_bits.append(f"Last verified: {last_verified}")
                    st.caption(" • ".join(source_bits))

            with tabs[1]:
                req_cols = st.columns(2)
                with req_cols[0]:
                    for title, values in [
                        ("Education", details.get("education", item.get("education_requirements"))),
                        ("Experience", details.get("experience", item.get("experience_requirements"))),
                        ("Language", details.get("languages", item.get("language_requirements"))),
                        ("Tests", details.get("tests", item.get("test_requirements"))),
                    ]:
                        if values and values != ["N/A"]:
                            _section(title, values)
                with req_cols[1]:
                    skills = item.get("metadata", {}).get("required_skills")
                    nationality = details.get("nationality", item.get("nationality_restrictions"))
                    documents = details.get("documents", item.get("required_documents"))
                    shown = False

                    if skills:
                        _section("Required skills", skills)
                        shown = True
                    if nationality and nationality != ["N/A"]:
                        _section("Eligibility / nationality", nationality)
                        shown = True
                    if documents and documents != ["N/A"]:
                        _section("Required documents", documents)
                        shown = True

                    if not shown:
                        st.caption("No additional structured requirements were stated.")

            with tabs[2]:
                money = st.columns(2)
                with money[0]:
                    st.markdown("#### Compensation")
                    any_money = False
                    for label, key in [
                        ("Salary / stipend", "compensation"),
                        ("Funding", "funding"),
                        ("Tuition", "tuition"),
                    ]:
                        value = item.get(key)
                        if value not in (None, "", "N/A"):
                            st.write(f"**{label}:** {value}")
                            any_money = True
                    if not any_money:
                        st.caption("No salary, stipend, funding, or tuition amount was stated.")

                with money[1]:
                    st.markdown("#### Conditions")
                    any_conditions = False
                    for label, key in [
                        ("Duration", "duration"),
                        ("Work mode", "work_mode"),
                        ("Application fee", "application_fee"),
                    ]:
                        value = item.get(key)
                        if value not in (None, "", "N/A"):
                            st.write(f"**{label}:** {value}")
                            any_conditions = True
                    benefits = details.get("benefits", item.get("benefits"))
                    if benefits and benefits != ["N/A"]:
                        _section("Benefits", benefits)
                        any_conditions = True
                    if not any_conditions:
                        st.caption("No additional conditions were stated.")

            with tabs[3]:
                app_cols = st.columns(2)
                with app_cols[0]:
                    st.markdown("#### Application facts")
                    deadline = item.get("deadline")
                    fee = item.get("application_fee")
                    documents = details.get("documents", item.get("required_documents"))
                    if deadline not in (None, "", "N/A"):
                        st.write(f"**Deadline:** {deadline}")
                    if fee not in (None, "", "N/A"):
                        st.write(f"**Application fee:** {fee}")
                    if documents and documents != ["N/A"]:
                        _section("Required documents", documents)
                    if (
                        deadline in (None, "", "N/A")
                        and fee in (None, "", "N/A")
                        and not documents
                    ):
                        st.caption("No additional application details were stated.")

                with app_cols[1]:
                    st.markdown("#### Application")
                    if item.get("application_url"):
                        st.link_button("🚀 Open application / source", item["application_url"], use_container_width=True)
                    else:
                        st.caption("No application link was found.")

            with tabs[4]:
                _render_match(item, profile)

            st.divider()
            action_cols = st.columns([1, 1, 1])
            with action_cols[0]:
                if item.get("application_url"):
                    st.link_button("🚀 Apply / Open", item["application_url"], use_container_width=True)
            with action_cols[1]:
                if st.button("📌 Save Opportunity", key=f"save_{_item_key(item)}", use_container_width=True):
                    st.session_state.setdefault("saved_opportunities", [])
                    if item.get("id") not in [x.get("id") for x in st.session_state["saved_opportunities"]]:
                        st.session_state["saved_opportunities"].append(item)
                    st.success("Saved to your opportunities.")
            with action_cols[2]:
                if st.button("📝 Add to Applications", key=f"app_{_item_key(item)}", use_container_width=True):
                    user_id = 1
                    opportunity_key = item.get("id") or item.get("application_url") or item.get("title")
                    existing = list_applications(user_id)
                    already_added = any(row["opportunity_key"] == opportunity_key for row in existing)
                    if not already_added:
                        save_application(
                            user_id,
                            {
                                "opportunity_key": opportunity_key,
                                "title": item.get("title") or "Untitled opportunity",
                                "organization": item.get("organization") or "N/A",
                                "status": "Saved",
                                "deadline": item.get("deadline"),
                                "next_action": "Review requirements and official application page",
                                "notes": item.get("application_url") or "",
                            },
                        )
                    st.success("Added to Applications." if not already_added else "Already in Applications.")


    if total_pages > 1:
        st.divider()
        nav = st.columns([1, 1, 2, 1, 1])
        with nav[0]:
            if st.button("← Previous", disabled=current_page <= 1, use_container_width=True):
                st.session_state.discovery_page = current_page - 1
                st.rerun()
        with nav[1]:
            if st.button("1", disabled=current_page == 1, use_container_width=True):
                st.session_state.discovery_page = 1
                st.rerun()
        with nav[2]:
            st.markdown(f"<div style='text-align:center;padding:.45rem'>Page <b>{current_page}</b> of <b>{total_pages}</b></div>", unsafe_allow_html=True)
        with nav[3]:
            if st.button(str(total_pages), disabled=current_page == total_pages, use_container_width=True):
                st.session_state.discovery_page = total_pages
                st.rerun()
        with nav[4]:
            if st.button("Next →", disabled=current_page >= total_pages, use_container_width=True):
                st.session_state.discovery_page = current_page + 1
                st.rerun()
