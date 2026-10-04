import asyncio
import json
import pathlib

import pytest

from models.opportunity import Opportunity


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    import database.db as db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    db.initialize_database()
    return db


# ----------------------------------------------------------------- navigation / pages
def test_navigation_is_header_with_expected_items_and_no_removed_pages():
    from ui import components as c
    assert c.NAV_ITEMS == ["Discover", "Scholarships", "Jobs", "Internships",
                           "Admissions", "Research", "CV & Letters", "🤖 Agent"]
    from ui.navigation import _page_table
    assert set(_page_table()) == set(c.NAV_ITEMS)
    src = open("ui/navigation.py", encoding="utf-8").read()
    assert "sidebar" not in src
    for gone in ("profile", "documents", "applications", "roadmap", "settings"):
        assert f"import {gone}" not in src and f"    {gone},\n" not in src


def test_dashboard_portals_use_real_daad_database_link():
    from ui.pages.dashboard import PORTALS
    urls = {name: url for name, _b, url in PORTALS}
    assert urls["DAAD"] == "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/"
    assert len(urls) >= 30 and all(u.startswith("https://") for u in urls.values())


def test_app_renders_each_page_headless(temp_db):
    from streamlit.testing.v1 import AppTest
    from ui import components as c
    at = AppTest.from_file(str(pathlib.Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30).run()
    assert not at.exception
    for page in c.NAV_ITEMS:
        at.session_state["nav_pills"] = page
        at.session_state["current_page"] = page
        at.run()
        assert not at.exception, (page, at.exception)


# ----------------------------------------------------------------- display cleaning
def test_clean_summary_drops_navigation_noise():
    from ui.components import clean_summary
    junk = "Home | About | Contact | Login » Skip to content Accept all cookies. Study Apply Research News Events Alumni. "
    real = "The programme offers fully funded places for international master's students in computer science and covers living costs."
    assert clean_summary(junk) == ""
    assert "fully funded" in clean_summary(junk + real)


def test_search_engine_urls_are_never_used_as_links():
    from ui.components import usable_url
    assert usable_url("https://www.google.com/search?q=x", "https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc") == ""
    assert usable_url("https://www.google.com/search?q=x", "https://www.daad.de/en/") == "https://www.daad.de/en/"


def test_unknown_values_display_as_not_stated():
    from ui.components import display_value
    assert display_value("N/A") == display_value(None) == "Not stated · see source"
    assert display_value("15 March 2027") == "15 March 2027"


# ----------------------------------------------------------------- discovery backend preserved
def test_source_manager_isolates_failures_and_exposes_diagnostics():
    from sources.base import BaseSource
    from sources.manager import SourceManager

    class Good(BaseSource):
        name = "Good"
        async def search(self, q, t=None, c=None):
            return [Opportunity(title="A", organization="B", opportunity_type="X")]

    class Bad(BaseSource):
        name = "Bad"
        async def search(self, q, t=None, c=None):
            raise RuntimeError("boom")

    m = SourceManager([Good(), Bad()])
    m.sources = [s for s in m.sources if s.name in {"Good", "Bad"}]
    out = asyncio.run(m.search("q"))
    assert len(out) == 1
    diag = {d["source"]: d for d in m.diagnostics}
    assert diag["Good"]["results"] == 1 and "boom" in diag["Bad"]["error"]


def test_study_degree_and_masters_share_admissions_lanes():
    from intelligence.discovery_planner import DiscoveryPlanner
    a = DiscoveryPlanner(None).build_plan("Study / Degree", fields=["AI"], countries=["Italy"])
    b = DiscoveryPlanner(None).build_plan("Master's", fields=["AI"], countries=["Italy"])
    assert a.queries == b.queries and a.opportunity_type == "Master's"


def test_masters_type_gate_rejects_internship_pages():
    from intelligence.opportunity_type import classify_opportunity
    internship = Opportunity(title="Summer internship", organization="X", opportunity_type="X", description="internship hiring now")
    ok, _ = classify_opportunity(internship, "Master's")
    assert not ok


def test_scholarship_library_still_loads():
    from intelligence.scholarship_library import load_library
    assert load_library()["entries"]


# ----------------------------------------------------------------- CV / documents
def test_llm_extracted_facts_must_be_supported_by_cv():
    from intelligence.profile_intelligence import ground_new_llm_facts
    cv = "Skills: Python, OpenCV.\nProjects\nGameVision AI - built a detector."
    updated = {"skills": ["python", "kubernetes"],
               "projects": [{"title": "GameVision AI", "description": "detector"},
                            {"title": "Relevant Coursework", "description": "x"},
                            {"title": "Invented Rocket Project", "description": "never in the CV"}]}
    out = ground_new_llm_facts(updated, {}, cv)
    assert out["skills"] == ["python"]
    assert [p["title"] for p in out["projects"]] == ["GameVision AI"]


def test_existing_profile_facts_survive_grounding():
    from intelligence.profile_intelligence import ground_new_llm_facts
    prev = {"skills": ["docker"], "projects": [{"title": "Manual Project", "description": "mine"}]}
    out = ground_new_llm_facts({"skills": ["docker"], "projects": prev["projects"]}, prev, "unrelated cv text")
    assert out["skills"] == ["docker"] and out["projects"][0]["title"] == "Manual Project"


def test_conservative_letter_never_adds_unsupported_skills():
    from documents.generator import conservative_letter, unsupported_skills
    profile = {"full_name": "Test User", "skills": ["python"], "education_text": "BS Computer Science"}
    text = conservative_letter("Cover Letter", profile, "We need Python, Docker and Kubernetes", "ML Intern", "Acme")
    assert "Test User" in text and "python" in text.lower()
    assert "docker" not in text.lower() and "kubernetes" not in text.lower()
    assert unsupported_skills("I use python and docker", profile) == ["docker"]


def test_letter_prompt_forbids_invention_and_excludes_budget():
    from documents.generator import build_letter_prompt
    prompt = build_letter_prompt("Motivation Letter", {"full_name": "A", "skills": ["python"], "budget": "SECRET"}, "details", "T", "O")
    assert "Use only facts explicitly supported by the applicant profile" in prompt
    assert "SECRET" not in prompt


def test_tailored_cv_orders_but_does_not_add_skills(tmp_path):
    from docx import Document
    from documents.generator import generate_tailored_cv
    opp = Opportunity(title="CV Role", organization="", opportunity_type="CV", metadata={"required_skills": ["docker", "python"]})
    path = generate_tailored_cv(str(tmp_path / "cv.docx"), {"full_name": "A", "skills": ["python", "sql"]}, opp)
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert "python, sql" in text and "docker" not in text


def test_profile_and_document_db_functions_still_work(temp_db):
    temp_db.save_profile(1, json.dumps({"full_name": "N"}))
    assert json.loads(temp_db.load_profile(1))["full_name"] == "N"
    temp_db.save_document(1, "cv.pdf", "Master CV", "/x", "text")
    rows = temp_db.list_documents(1)
    assert rows and temp_db.delete_document(rows[0]["id"], 1) == "/x"


def test_generate_external_falls_through_providers():
    from llm.manager import LLMManager
    from llm.base import BaseLLM

    class Down(BaseLLM):
        name = "gemini"
        async def generate(self, prompt, system=""):
            raise RuntimeError("quota")

    class Up(BaseLLM):
        name = "groq"
        async def generate(self, prompt, system=""):
            return "ok"

    m = LLMManager()
    m.providers = [Down(), Up(), m.providers[-1]]
    assert asyncio.run(m.generate_external("x")) == "ok"


def test_discovery_keeps_pages_without_snippet_deadline_and_rejects_wrong_type_or_expired():
    from sources.base import BaseSource
    from sources.manager import SourceManager
    import intelligence.discovery_planner as dp
    import intelligence.discovery_service as ds

    good = ("DAAD scholarship for international master's students in Artificial Intelligence. Application deadline: 15 March 2099. "
            "Funding: full scholarship with monthly stipend. How to apply: submit your application online. Eligibility applies.")
    pages = {"https://www.daad.de/a": good,
             "https://www.x.de/old": good.replace("15 March 2099", "10 January 2020"),
             "https://www.y.de/job": "Software engineer job vacancy hiring now. Apply now. Scholarships are not offered. Application deadline: 1 May 2099."}

    class Fake(BaseSource):
        name = "Fake"
        async def search(self, q, t=None, c=None):
            return [Opportunity(title=u.rsplit("/", 1)[1], organization="o", opportunity_type="X", description="snippet",
                                application_url=u, source_url=u) for u in pages]

    async def fake_fetch(url, timeout=5, max_chars=30000):
        return {"text": pages[url]} if url in pages else {}

    real_fetch, real_mgr = dp.fetch_page, ds.default_source_manager
    dp.fetch_page = fake_fetch
    ds.default_source_manager = lambda: SourceManager([Fake()])
    try:
        results, _ = ds.search_opportunities("", "Scholarship", [], ["Germany"], ["Artificial Intelligence"], {}, "Master's")
    finally:
        dp.fetch_page, ds.default_source_manager = real_fetch, real_mgr
    assert [r.title for r in results] == ["a"]


def test_library_source_gives_keyless_candidates_and_catalogues_are_flagged():
    from sources.scholarship_library_source import ScholarshipLibrarySource
    items = asyncio.run(ScholarshipLibrarySource().search("", "Scholarship", "Germany"))
    assert any(i.metadata.get("library_source_kind") == "catalogue" and "daad" in i.application_url for i in items)
    assert asyncio.run(ScholarshipLibrarySource().search("", "Job", "Germany")) == []


def test_masters_level_matches_library_levels_and_library_is_broad():
    from intelligence.scholarship_library import load_library, scholarship_entries
    assert len(load_library()["entries"]) >= 50
    assert scholarship_entries("Germany", "Master's")


def test_collection_expander_follows_real_links(monkeypatch):
    import intelligence.collection_expander as ce
    html = ('<html><body><a href="/s/erasmus-scholarship-ai">Erasmus scholarship for AI students</a>'
            '<a href="/about">About us and our history</a>'
            '<a href="https://other.org/x-scholarship-page">Elsewhere scholarship page link</a></body></html>')

    async def fake_html(url, timeout=6, max_chars=400000):
        return html
    monkeypatch.setattr(ce, "fetch_html", fake_html)
    monkeypatch.setattr(ce, "filter_current_opportunities", lambda xs: xs)
    parent = Opportunity(title="Catalogue", organization="x", opportunity_type="SCHOLARSHIP",
                         application_url="https://cat.example.org/list", source_url="https://cat.example.org/list")
    out = asyncio.run(ce.expand_collection(parent, "Scholarship"))
    assert [o.application_url for o in out] == ["https://cat.example.org/s/erasmus-scholarship-ai"]


def test_bing_redirect_links_are_unwrapped():
    import base64
    from sources.web import unwrap_bing_url
    real = "https://www.chevening.org/scholarships/"
    token = "a1" + base64.urlsafe_b64encode(real.encode()).decode().rstrip("=")
    assert unwrap_bing_url(f"https://www.bing.com/ck/a?!&&p=x&u={token}&ntb=1") == real
    assert unwrap_bing_url("https://www.daad.de/en/") == "https://www.daad.de/en/"


def test_same_page_from_several_country_searches_becomes_one_result():
    from intelligence.discovery_service import canonical_url, merge_same_page
    a = Opportunity(title="Konrad Zuse", organization="eliza.school", opportunity_type="S", country="Denmark", application_url="https://www.eliza.school/zuse/?utm_source=x")
    b = Opportunity(title="Konrad Zuse", organization="eliza.school", opportunity_type="S", country="Sweden", application_url="https://eliza.school/zuse")
    c = Opportunity(title="Other", organization="o", opportunity_type="S", country="Denmark", application_url="https://o.org/p")
    out = merge_same_page([a, b, c])
    assert [o.title for o in out] == ["Konrad Zuse", "Other"]
    assert out[0].country is None and out[0].metadata["searched_countries"] == ["Denmark", "Sweden"]
    assert out[1].country == "Denmark"
    assert canonical_url("https://www.a.org/x/#frag") == canonical_url("https://a.org/x")


def test_result_cards_use_unique_widget_keys(temp_db):
    from streamlit.testing.v1 import AppTest
    dup = {"title": "Same", "organization": "o", "opportunity_type": "S", "application_url": "https://o.org/p", "metadata": {}}
    at = AppTest.from_file(str(pathlib.Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    at.session_state["nav_pills"] = "Scholarships"
    at.session_state["current_page"] = "Scholarships"
    at.session_state["res::Scholarship"] = [dup, dict(dup, country="Sweden")]
    at.run()
    assert not at.exception


# ----------------------------------------------------------------- jobs
def test_clean_role_query_strips_search_decoration():
    from sources.jobs.common import clean_role_query
    q = "(site:eures.europa.eu OR site:arbeitsagentur.de) Python Developer Germany 2026 current open hiring vacancy"
    assert clean_role_query(q, "Germany") == "python developer"


def test_aggregate_job_listing_pages_are_detected():
    from intelligence.opportunity_type import is_aggregate_listing

    def mk(title, url="https://x.com/job/123"):
        return Opportunity(title=title, organization="o", opportunity_type="JOB", application_url=url, source_url=url)
    assert is_aggregate_listing(mk("100 jobs available in Berlin"), "Job")
    assert is_aggregate_listing(mk("Software Engineer Jobs in Berlin"), "Job")
    assert is_aggregate_listing(mk("Careers", "https://acme.com/careers"), "Job")
    assert is_aggregate_listing(mk("Find jobs"), "Job")
    assert not is_aggregate_listing(mk("Senior Python Engineer at Acme"), "Job")
    assert not is_aggregate_listing(mk("Senior Python Engineer", "https://acme.com/jobs/senior-python-engineer-123"), "Job")
    assert not is_aggregate_listing(mk("100 jobs available"), "Scholarship")


def test_jobs_are_returned_as_individual_postings(monkeypatch):
    import sources.jobs.remotive as rem
    import intelligence.discovery_service as ds
    from sources.manager import SourceManager
    from datetime import datetime, timezone, timedelta

    fresh = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    desc = "<p>" + "We are hiring a Python engineer to build ML services and APIs for our platform. " * 4 + "Apply now.</p>"
    payload = {"jobs": [
        {"id": 1, "url": "https://remotive.com/job/1", "title": "Python Engineer", "company_name": "Acme", "category": "Software",
         "tags": ["python"], "job_type": "full_time", "publication_date": fresh, "candidate_required_location": "Worldwide", "salary": "", "description": desc},
        {"id": 2, "url": "https://remotive.com/job/2", "title": "Senior Python Developer", "company_name": "Beta", "category": "Software",
         "tags": ["python"], "job_type": "full_time", "publication_date": fresh, "candidate_required_location": "USA Only", "salary": "", "description": desc},
        {"id": 3, "url": "https://remotive.com/job/3", "title": "Python Engineer (old)", "company_name": "Gamma", "category": "Software",
         "tags": ["python"], "job_type": "full_time", "publication_date": old, "candidate_required_location": "Worldwide", "salary": "", "description": desc},
        {"id": 4, "url": "https://remotive.com/job/4", "title": "Python Intern", "company_name": "Delta", "category": "Software",
         "tags": ["python"], "job_type": "internship", "publication_date": fresh, "candidate_required_location": "Worldwide", "salary": "", "description": desc},
    ]}

    async def fake_json(url, params=None, ttl=3600, timeout=20.0):
        return payload
    monkeypatch.setattr(rem, "cached_json", fake_json)
    monkeypatch.setattr(ds, "default_source_manager", lambda: SourceManager([rem.RemotiveSource()]))
    results, _ = ds.search_opportunities("", "Job", ["Python Developer"], ["Pakistan"], [], {})
    titles = sorted(r.title for r in results)
    assert titles == ["Python Engineer"]            # US-only, 200-day-old and internship postings excluded
    assert results[0].application_url == "https://remotive.com/job/1" and results[0].work_mode == "Remote"


def test_page_title_extraction_drops_site_suffix():
    from sources.webfetch import extract_page_title
    html = '<html><head><title>Konrad Zuse Master\'s in AI Scholarship | eliza.school</title></head><body><h1>x</h1></body></html>'
    title, site = extract_page_title(html)
    assert title == "Konrad Zuse Master's in AI Scholarship" and site == "eliza.school"


def test_cv_letters_link_bar_fills_details(temp_db, monkeypatch):
    import sources.webfetch as wf
    from streamlit.testing.v1 import AppTest

    async def fake_page(url, timeout=8.0, max_chars=12000):
        return {"title": "ML Engineer", "site": "Acme", "text": "Acme is hiring a machine learning engineer. " * 12}
    monkeypatch.setattr(wf, "fetch_page", fake_page)
    at = AppTest.from_file(str(pathlib.Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    at.session_state["nav_pills"] = "CV & Letters"
    at.session_state["current_page"] = "CV & Letters"
    at.run()
    at.text_input(key="cvl_link").set_value("https://acme.com/jobs/ml-engineer").run()
    next(b for b in at.button if b.key == "cvl_fetch").click().run()
    assert not at.exception
    assert "machine learning engineer" in at.session_state["cvl_details"]
    assert at.session_state["cvl_title"] == "ML Engineer" and at.session_state["cvl_org"] == "Acme"


def test_job_results_render_as_individual_cards(temp_db):
    from streamlit.testing.v1 import AppTest
    jobs = [{"title": f"Python Engineer {i}", "organization": f"Co{i}", "opportunity_type": "JOB", "city": "Remote",
             "work_mode": "Remote", "application_url": f"https://x.com/job/{i}", "source_url": f"https://x.com/job/{i}",
             "metadata": {"structured_listing": True, "posted_date": "2026-10-01", "job_type": "full_time"}} for i in range(3)]
    at = AppTest.from_file(str(pathlib.Path(__file__).resolve().parents[1] / "app.py"), default_timeout=30)
    at.session_state["nav_pills"] = "Jobs"
    at.session_state["current_page"] = "Jobs"
    at.session_state["res::Job"] = jobs
    at.run()
    assert not at.exception
    assert sum(1 for b in at.button if b.label == "Analyze & prepare") == 3
    assert any("job postings" in str(s.value) for s in at.success)
