import asyncio
import json
import re
from pathlib import Path

import streamlit as st

from database.db import delete_document, list_documents, load_profile, save_document, save_profile
from documents.cv_intelligence import extract_cv_signals
from documents.extract import extract_text
from documents.generator import (
    LETTER_KINDS, LETTER_SYSTEM, build_letter_prompt, conservative_letter, evidence_strength,
    generate_tailored_cv, letter_docx_bytes, unsupported_skills,
)
from intelligence.profile_intelligence import (
    build_profile_from_cv, build_profile_from_cv_with_llm, clean_project_clutter, ground_new_llm_facts,
)
from intelligence.skill_taxonomy import extract_skills, merge_skills
from llm.manager import LLMManager
from models.opportunity import Opportunity
from ui import components as c
from core.session import user_id, user_upload_dir

DOC_KINDS = ["Tailored CV", "Cover Letter", "Motivation Letter", "Statement of Purpose"]
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ------------------------------------------------------------------ helpers
def _profile() -> dict:
    try:
        return json.loads(load_profile(user_id()) or "{}")
    except Exception:
        return {}


def _csv(value: str) -> list[str]:
    out, seen = [], set()
    for item in re.split(r"[,\n]", value or ""):
        item = item.strip()
        if item and item.casefold() not in seen:
            seen.add(item.casefold()); out.append(item)
    return out


def _ver() -> int:
    return st.session_state.setdefault("cvl_ver", 0)


def _k(name: str) -> str:
    return f"cvl_{name}_{_ver()}"


def _reload_profile_widgets():
    """Force every profile widget to re-read the saved profile on the next run."""
    st.session_state["cvl_ver"] = _ver() + 1
    st.session_state.pop("cvl_projects", None)
    st.session_state.pop("cvl_tests", None)


def _education_text(p: dict) -> str:
    text = p.get("education_text")
    if text:
        return str(text)
    edu = p.get("education")
    if isinstance(edu, str):
        return edu
    if isinstance(edu, list):
        return "\n".join(str(e.get("raw") or " ".join(str(v) for v in e.values() if v)) if isinstance(e, dict) else str(e) for e in edu)
    return ""


# ------------------------------------------------------------------ master CV
def _process_cv(uploaded) -> None:
    safe_name = Path(uploaded.name).name
    path = user_upload_dir() / safe_name
    path.write_bytes(uploaded.getbuffer())
    try:
        text = extract_text(str(path))
    except Exception as exc:
        st.error(f"Could not read this file: {exc}")
        return
    if not text.strip():
        st.error("No readable text was found in this CV. If it is a scanned PDF, upload a text-based PDF or DOCX.")
        return
    # Replace any previous Master CV record so there is exactly one.
    for row in list_documents(user_id()):
        if row["document_type"] == "Master CV" and row["filename"] != safe_name:
            old = delete_document(row["id"], user_id())
            if old:
                try:
                    Path(old).unlink(missing_ok=True)
                except Exception:
                    pass
    save_document(user_id(), safe_name, "Master CV", str(path), text)

    previous = _profile()
    updated = build_profile_from_cv(text, previous)            # deterministic: skills/email/sections, never projects
    used_llm = False
    manager = LLMManager()
    if manager.has_external_provider:
        try:
            llm_profile = asyncio.run(build_profile_from_cv_with_llm(text, updated))
            updated = ground_new_llm_facts(llm_profile, previous, text)   # keep only CV-supported additions
            used_llm = True
        except Exception as exc:
            st.warning(f"AI-assisted CV reading was unavailable, so basic extraction was used ({type(exc).__name__}).")
    updated["projects"] = clean_project_clutter(updated.get("projects", []))
    updated["skills"] = merge_skills(updated.get("skills", []))
    save_profile(user_id(), json.dumps(updated))
    st.session_state["cvl_last_extract"] = {"name": safe_name, "llm": used_llm, "skills": extract_cv_signals(text)["skills"]}
    _reload_profile_widgets()


def _section_master_cv(profile: dict) -> None:
    st.subheader("Master CV")
    docs = [r for r in list_documents(user_id()) if r["document_type"] == "Master CV"]
    if docs:
        st.caption(f"Current Master CV: **{docs[0]['filename']}**")
    uploaded = st.file_uploader("Upload / replace Master CV", type=["pdf", "docx", "txt", "md"], key="cvl_cv_upload")
    if uploaded and st.button("Read CV into profile", type="primary", key="cvl_read_cv"):
        with st.spinner("Reading your CV…"):
            _process_cv(uploaded)
        st.rerun()

    info = st.session_state.get("cvl_last_extract")
    if info:
        st.success(f"{info['name']} processed. " + ("AI-assisted reading was used; " if info["llm"] else "") +
                   "only facts supported by the CV were merged.")

    p = _profile()
    has = {
        "Education": bool(_education_text(p).strip()),
        "Skills": bool(p.get("skills")),
        "Experience": bool(str(p.get("experience", "")).strip()),
        "Projects": bool(p.get("projects")),
        "Certificates / Tests": bool(p.get("tests") or p.get("certifications")),
    }
    st.write("  ".join(f"{'✓' if ok else '○'} {label}" for label, ok in has.items()))
    if not LLMManager().has_external_provider:
        st.caption("No AI provider configured: skills and sections are extracted by rules only. Projects stay manual so headings never become fake projects.")


# ------------------------------------------------------------------ profile
def _init_lists(p: dict) -> None:
    if "cvl_projects" not in st.session_state:
        st.session_state["cvl_projects"] = clean_project_clutter(p.get("projects", []))
    if "cvl_tests" not in st.session_state:
        st.session_state["cvl_tests"] = [
            {"name": t.get("name", ""), "has_result": bool(t.get("has_result")), "score": t.get("score", ""), "details": t.get("details", "")}
            for t in (p.get("tests") or []) if isinstance(t, dict)
        ]


def _collect_projects() -> list[dict]:
    return [{"title": str(st.session_state.get(_k(f"ptitle{i}"), "") or "").strip(),
             "description": str(st.session_state.get(_k(f"pdesc{i}"), "") or "").strip()}
            for i in range(len(st.session_state.get("cvl_projects", [])))]


def _collect_tests() -> list[dict]:
    tests = []
    for i in range(len(st.session_state.get("cvl_tests", []))):
        name = str(st.session_state.get(_k(f"tname{i}"), "") or "").strip()
        if not name:
            continue
        has = st.session_state.get(_k(f"thas{i}"), "No") == "Yes"
        tests.append({"name": name, "has_result": has,
                      "score": str(st.session_state.get(_k(f"tscore{i}"), "") or "").strip() if has else "",
                      "details": str(st.session_state.get(_k(f"tdet{i}"), "") or "").strip() if has else ""})
    return tests


def _add_project():
    st.session_state["cvl_projects"] = _collect_projects() + [{"title": "", "description": ""}]


def _remove_project():
    items = _collect_projects()
    st.session_state["cvl_projects"] = items[:-1]
    _bump_after_list_change()


def _add_test():
    st.session_state["cvl_tests"] = _collect_tests_raw() + [{"name": "", "has_result": False, "score": "", "details": ""}]


def _collect_tests_raw() -> list[dict]:
    return [{"name": str(st.session_state.get(_k(f"tname{i}"), "") or ""),
             "has_result": st.session_state.get(_k(f"thas{i}"), "No") == "Yes",
             "score": str(st.session_state.get(_k(f"tscore{i}"), "") or ""),
             "details": str(st.session_state.get(_k(f"tdet{i}"), "") or "")}
            for i in range(len(st.session_state.get("cvl_tests", [])))]


def _remove_test():
    items = _collect_tests_raw()
    st.session_state["cvl_tests"] = items[:-1]
    _bump_after_list_change()


def _bump_after_list_change():
    # Items keep their text in the lists above; fresh widget keys make Streamlit show exactly those lists.
    projects = st.session_state.get("cvl_projects", [])
    tests = st.session_state.get("cvl_tests", [])
    st.session_state["cvl_ver"] = _ver() + 1
    st.session_state["cvl_projects"], st.session_state["cvl_tests"] = projects, tests


def _save_profile(profile: dict) -> None:
    data = dict(_profile())
    projects = clean_project_clutter([x for x in _collect_projects() if x["title"] or x["description"]])
    education = st.session_state.get(_k("education"), "")
    data.update({
        "full_name": st.session_state.get(_k("name"), "").strip(), "email": st.session_state.get(_k("email"), "").strip(),
        "country": st.session_state.get(_k("country"), "").strip(), "city": st.session_state.get(_k("city"), "").strip(),
        "skills": merge_skills(_csv(st.session_state.get(_k("skills"), ""))),
        "career_interests": _csv(st.session_state.get(_k("career"), "")),
        "study_interests": _csv(st.session_state.get(_k("study"), "")),
        "research_interests": _csv(st.session_state.get(_k("research"), "")),
        "preferred_countries": _csv(st.session_state.get(_k("pref"), "")),
        "experience": st.session_state.get(_k("experience"), ""),
        "education_text": education,
        "education": [{"raw": education}] if education.strip() else [],
        "projects": projects, "tests": _collect_tests(),
    })
    save_profile(user_id(), json.dumps(data))
    st.session_state["cvl_projects"] = projects
    st.session_state["cvl_saved_flag"] = True


def _section_profile() -> None:
    p = _profile()
    _init_lists(p)
    st.subheader("Your profile")
    st.caption("Used for matching, discovery and every document you generate. Edit anything the CV missed.")
    a, b = st.columns(2)
    a.text_input("Full name", p.get("full_name", ""), key=_k("name"))
    b.text_input("Email", p.get("email", ""), key=_k("email"))
    a, b = st.columns(2)
    a.text_input("Country", p.get("country", ""), key=_k("country"))
    b.text_input("City", p.get("city", ""), key=_k("city"))
    st.text_area("Skills (comma separated)", ", ".join(p.get("skills", []) or []), key=_k("skills"))
    st.text_area("Education", _education_text(p), key=_k("education"), height=110,
                 placeholder="e.g. BS Computer Science (AI), AWKUM — CGPA 3.45/4.00")
    st.text_area("Experience", str(p.get("experience", "") or ""), key=_k("experience"), height=140)
    st.text_area("Career interests (comma separated)", ", ".join(p.get("career_interests", []) or []), key=_k("career"), height=70)
    with st.expander("More: study / research interests, preferred countries"):
        st.text_area("Study interests", ", ".join(p.get("study_interests", []) or []), key=_k("study"), height=70)
        st.text_area("Research interests", ", ".join(p.get("research_interests", []) or []), key=_k("research"), height=70)
        st.text_area("Preferred countries", ", ".join(p.get("preferred_countries", []) or []), key=_k("pref"), height=70)

    st.markdown("**Projects** — add your own; they are never guessed from CV headings.")
    for i, proj in enumerate(st.session_state["cvl_projects"]):
        st.text_input(f"Project {i + 1} name", proj.get("title", ""), key=_k(f"ptitle{i}"))
        st.text_area(f"Project {i + 1} — what did you build / do?", proj.get("description", ""), key=_k(f"pdesc{i}"), height=100)
    b1, b2, _ = st.columns([1, 1, 2])
    b1.button("➕ Add project", key="cvl_addp", on_click=_add_project, use_container_width=True)
    b2.button("🗑 Remove last", key="cvl_remp", on_click=_remove_project, use_container_width=True,
              disabled=not st.session_state["cvl_projects"])

    with st.expander(f"Certificates & tests ({len(st.session_state['cvl_tests'])})"):
        for i, t in enumerate(st.session_state["cvl_tests"]):
            st.text_input(f"Test / certificate {i + 1}", t.get("name", ""), key=_k(f"tname{i}"), placeholder="IELTS, GRE, a certificate…")
            has = st.radio("Have a result?", ["No", "Yes"], index=1 if t.get("has_result") else 0, horizontal=True, key=_k(f"thas{i}"))
            if has == "Yes":
                st.text_input("Score / result", t.get("score", ""), key=_k(f"tscore{i}"))
                st.text_input("Details (date, validity…)", t.get("details", ""), key=_k(f"tdet{i}"))
        t1, t2, _ = st.columns([1, 1, 2])
        t1.button("➕ Add", key="cvl_addt", on_click=_add_test, use_container_width=True)
        t2.button("🗑 Remove last", key="cvl_remt", on_click=_remove_test, use_container_width=True,
                  disabled=not st.session_state["cvl_tests"])

    st.button("💾 Save profile", type="primary", key="cvl_save", on_click=_save_profile, args=(p,))
    if st.session_state.pop("cvl_saved_flag", False):
        st.success("Profile saved.")

    docs = list_documents(user_id())
    with st.expander(f"Uploaded documents ({len(docs)})"):
        if not docs:
            st.caption("Nothing uploaded yet.")
        for row in docs:
            x, y = st.columns([5, 1])
            x.write(f"**{row['filename']}** — {row['document_type']}")
            if y.button("Remove", key=f"cvl_rm_{row['id']}"):
                old = delete_document(row["id"], user_id())
                if old:
                    try:
                        Path(old).unlink(missing_ok=True)
                    except Exception:
                        pass
                st.rerun()
        st.caption("Removing a file never deletes facts already saved in your profile.")


# ------------------------------------------------------------------ documents
def _generate(kind: str, details: str, title: str, org: str) -> dict:
    profile = _profile()
    notice = ""
    if kind == "Tailored CV":
        opp = Opportunity(title=title.strip(), organization=org.strip(), opportunity_type="CV",
                          metadata={"required_skills": extract_skills(f"{title} {details}")})
        path = user_upload_dir() / "tailored_cv.docx"
        generate_tailored_cv(str(path), profile, opp)
        return {"kind": kind, "path": str(path), "text": "", "notice": notice}

    strength = evidence_strength(profile)
    text = ""
    if strength >= 2 and LLMManager().has_external_provider:
        try:
            text = asyncio.run(LLMManager().generate_external(build_letter_prompt(kind, profile, details, title, org), LETTER_SYSTEM)).strip()
        except Exception:
            notice = "AI providers were unavailable, so a conservative template draft was created from your profile."
    elif strength < 2:
        notice = "Your profile has little evidence yet, so this is a conservative draft. Upload your CV or fill in education, skills and experience for a stronger letter."
    elif not LLMManager().has_external_provider:
        notice = "No AI provider is configured, so a conservative template draft was created from your profile."
    if not text:
        text = conservative_letter(kind, profile, details, title, org)
    # The target title/organization come from the opportunity, not from claims about the applicant.
    extra = unsupported_skills(text, profile, ignore=title)
    extra = [x for x in extra if x not in set(extract_skills(org))]
    if extra:
        notice = (notice + " " if notice else "") + "Review before use — these skills appear in the draft but not in your profile: " + ", ".join(extra) + "."
    return {"kind": kind, "path": "", "text": text, "notice": notice}


def _fetch_link() -> None:
    """on_click callback: read the page behind a pasted link and fill the form with structured, grounded facts."""
    from intelligence.link_extractor import content_text, details_block, extract_opportunity
    from sources.webfetch import fetch_page
    st.session_state.pop("cvl_link_info", None)
    st.session_state.pop("cvl_link_closed", None)
    url = (st.session_state.get("cvl_link") or "").strip()
    if not url:
        st.session_state["cvl_link_msg"] = ("warn", "Paste a link first.")
        return
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
        st.session_state["cvl_link"] = url
    if c.is_search_engine_url(url):
        st.session_state["cvl_link_msg"] = ("warn", "That is a search-engine link. Open the actual opportunity page and paste its link.")
        return
    page = asyncio.run(fetch_page(url, timeout=10, max_chars=12000)) or {}
    if len(content_text(page)) < 200:
        st.session_state["cvl_link_msg"] = ("warn", "I couldn't read enough from that page (it may need a login or load its content with JavaScript). Paste the opportunity text below instead.")
        return
    manager = LLMManager()
    info = asyncio.run(extract_opportunity(page, url, manager))
    # Warn (never silently continue) when the page says the opportunity is over.
    from types import SimpleNamespace
    from intelligence.freshness import availability_reason
    still_open, why = availability_reason(SimpleNamespace(
        title=info.get("title", ""), deadline=info.get("deadline", ""), description=page.get("text", ""),
        metadata={"summary": "", "search_snippet": ""}))
    st.session_state["cvl_link_closed"] = "" if still_open or "no explicit" in why.casefold() else why
    st.session_state["cvl_title"] = info.get("title", "")
    st.session_state["cvl_org"] = info.get("organization", "")
    st.session_state["cvl_details"] = details_block(info, url)
    st.session_state["cvl_link_info"] = info
    if info.get("used_llm"):
        st.session_state["cvl_link_msg"] = ("ok", "Read the page with AI-assisted extraction. Every field below comes from the page itself; check it, then generate.")
    elif manager.has_external_provider:
        st.session_state["cvl_link_msg"] = ("ok", "Read the page with rule-based extraction (the AI provider did not answer this time). Check the fields below.")
    else:
        st.session_state["cvl_link_msg"] = ("ok", "Read the page with rule-based extraction. Add a Gemini or Groq key in .env for cleaner summaries and requirement lists.")


def _render_link_summary() -> None:
    info = st.session_state.get("cvl_link_info")
    if not info:
        return
    closed = st.session_state.get("cvl_link_closed")
    if closed:
        st.error(f"⚠️ This opportunity looks closed or expired ({closed}). Check the source before spending time on an application.")
    with st.container(border=True):
        facts = [("Type", info.get("kind") or "Other"), ("Deadline", info.get("deadline") or "Not found"),
                 ("Funding / pay", info.get("funding") or "Not found"), ("Location", info.get("location") or "Not found")]
        for col, (label, value) in zip(st.columns(len(facts)), facts):
            col.markdown(c.fact(label, value), unsafe_allow_html=True)
        if info.get("summary"):
            st.write(info["summary"])
        left, right = st.columns(2)
        if info.get("eligibility"):
            left.markdown("**Eligibility**\n" + "\n".join(f"- {x}" for x in info["eligibility"]))
        if info.get("requirements"):
            right.markdown("**Requirements**\n" + "\n".join(f"- {x}" for x in info["requirements"]))
        if info.get("how_to_apply"):
            st.caption("How to apply: " + info["how_to_apply"])


def _section_create() -> None:
    st.subheader("Create application document")
    st.caption("Paste a link to the opportunity, or paste its text — job description, scholarship details, programme page, research position. Documents use only facts from your profile.")
    l1, l2 = st.columns([5, 1], vertical_alignment="bottom")
    l1.text_input("Opportunity link (optional)", key="cvl_link",
                  placeholder="Paste the job / scholarship / programme page link and I will read it for you")
    l2.button("Fetch details", key="cvl_fetch", on_click=_fetch_link, use_container_width=True)
    msg = st.session_state.get("cvl_link_msg")
    if msg:
        (st.success if msg[0] == "ok" else st.warning)(msg[1])
    _render_link_summary()
    a, b = st.columns(2)
    title = a.text_input("Opportunity title (optional)", key="cvl_title")
    org = b.text_input("Organization (optional)", key="cvl_org")
    details = st.text_area("Opportunity details", key="cvl_details", height=200,
                           placeholder="Paste the opportunity description here…")
    kind = st.radio("Document", DOC_KINDS, horizontal=True, key="cvl_kind")
    strength = evidence_strength(_profile())
    if strength == 0:
        st.info("Add your CV or profile details first — there is nothing to build the document from yet.")
    if st.button("✨ Generate", type="primary", key="cvl_generate", disabled=strength == 0):
        if not details.strip() and not title.strip():
            st.warning("Add the opportunity details (or at least a title) so the document can be tailored.")
        else:
            with st.spinner("Generating…"):
                try:
                    st.session_state["cvl_result"] = _generate(kind, details, title, org)
                except Exception as exc:
                    st.error(f"Could not generate the document: {exc}")

    res = st.session_state.get("cvl_result")
    if not res:
        return
    st.divider()
    if res.get("notice"):
        st.warning(res["notice"])
    if res["kind"] == "Tailored CV":
        path = Path(res["path"])
        if path.exists():
            st.success("Tailored CV ready — built only from your saved profile. Review and edit before submitting.")
            st.download_button("⬇️ Download Tailored CV (.docx)", path.read_bytes(), file_name="Tailored_CV.docx", mime=DOCX_MIME, key="cvl_dl_cv")
        return
    edited = st.text_area(f"{res['kind']} (editable)", res["text"], height=380, key="cvl_edit_" + str(abs(hash(res["text"]))))
    d1, d2, _ = st.columns([1, 1, 2])
    d1.download_button("⬇️ Word (.docx)", letter_docx_bytes(res["kind"], edited), file_name=f"{res['kind'].replace(' ', '_')}.docx", mime=DOCX_MIME, key="cvl_dl_docx")
    d2.download_button("⬇️ Text (.txt)", edited.encode("utf-8"), file_name=f"{res['kind'].replace(' ', '_')}.txt", key="cvl_dl_txt")
    st.caption("You submit applications yourself. Opportune AI never submits anything for you.")


def render():
    st.header("📄 CV & Letters")
    st.caption("Your master CV and profile in one place — and the documents built from them.")
    profile = _profile()
    _section_master_cv(profile)
    st.divider()
    with st.expander("Profile details", expanded=not profile.get("full_name") and not profile.get("skills")):
        _section_profile()
    st.divider()
    _section_create()
