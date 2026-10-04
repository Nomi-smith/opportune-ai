"""Regression tests for the 'jobs / postdocs / generic pages show up in scholarship results' bugs."""
import asyncio
from datetime import datetime, timedelta, timezone

import intelligence.discovery_planner as dp
import intelligence.discovery_service as ds
from intelligence.freshness import _dates, availability_reason
from intelligence.relevance import (detect_levels, is_navigational_title, is_scholarship_index, level_ok,
                                    looks_like_job_posting, relevance_gate)
from intelligence.source_content import extract_deadline, extract_funding
from models.opportunity import Opportunity
from sources.base import BaseSource
from sources.jobs.arbeitnow import ArbeitnowSource
from sources.jobs.common import build_job
from sources.manager import SourceManager
from sources.research.openalex import OpenAlexSource


# ------------------------------------------------------------------ sources must respect the requested type
def test_job_board_and_author_sources_stay_silent_for_other_types():
    for kind in ("Scholarship", "Research", "Master's", None):
        assert asyncio.run(ArbeitnowSource().search("cybersecurity", kind, "Germany")) == []
    for kind in ("Scholarship", "Job", "Master's"):
        assert asyncio.run(OpenAlexSource().search("cybersecurity", kind, None)) == []


# ------------------------------------------------------------------ title / body classifiers
def test_job_titles_and_postings_are_recognised():
    for title in ["Product Manager", "QA Engineer Mobile", "Corporate Account Executive", "Customer Support Specialist",
                  "Praktikum Trainer*innen-Entwicklung (m/w/d)", "Program Director (f/m/d) - Executive MBA Program",
                  "Distinguished PQC Cryptography & Architecture Leader"]:
        assert looks_like_job_posting(title, ""), title
    assert not looks_like_job_posting("Future Leader Scholarship", "Eligibility and how to apply")
    assert looks_like_job_posting("Opportunity", "Responsibilities: ... We are looking for ... What we offer: ... full-time")


def test_navigation_and_index_titles():
    assert is_navigational_title("Faculty & Guest Speakers")
    assert is_navigational_title("Selecting an Eligible Study Program")
    assert is_scholarship_index("Scholarship Database")
    assert is_scholarship_index("Scholarship opportunities directory")
    assert not is_scholarship_index("Chevening Scholarship")
    assert not is_navigational_title("Chinese Government Scholarship Application (Academic Year 2026/2027)")


def test_level_gate():
    assert not level_ok("Humboldt Postdoc Fellowships", "", "Master's")[0]
    assert not level_ok("DAAD PhD Scholarship", "for doctoral candidates", "Master's")[0]
    assert level_ok("Chevening Scholarship", "one-year master's degrees", "Master's")[0]
    assert level_ok("Some Scholarship", "no level stated here", "Master's")[0]
    assert level_ok("Any", "bachelor", "Any")[0]
    assert detect_levels("Master's and PhD students") == ["Master's", "PhD"]


# ------------------------------------------------------------------ extractors never return fragments
def test_deadline_extraction_returns_only_dates():
    assert extract_deadline("Customer Support. Deadline: is at risk Communicate clear, timely updates") is None
    assert extract_deadline("Application deadline: 3 November 2099 (CET).") == "3 November 2099"
    assert extract_deadline("Deadlines: 25 April and 25 October each year") == "25 April / 25 October"
    assert extract_deadline("We review applications on a rolling basis.") == "Rolling basis"


def test_funding_extraction_needs_real_evidence():
    assert extract_funding("The current application window is open. and the current application window") is None
    assert extract_funding("Boren Awards. s applicants must be matriculated in an associate's degree program.") is None
    assert "fully funded" in extract_funding("This programme is fully funded by the government. Apply online.")
    assert "stipend" in extract_funding("Funding: Monthly stipend according to DAAD rates, tuition waiver").lower()


def test_dates_cover_abbreviations_and_numeric_forms():
    ds_ = _dates("Deadline 3rd of November 2026, Nov. 5, 2026 and 31/10/2026")
    assert len(ds_) == 3
    assert availability_reason(Opportunity(title="x", organization="o", opportunity_type="X",
                                           description="Visa expired for some. Apply now. Deadline: 3 November 2099"))[0]
    assert not availability_reason(Opportunity(title="x", organization="o", opportunity_type="X",
                                               description="This job has expired."))[0]


# ------------------------------------------------------------------ full pipeline, replaying the screenshots
GOOD = ("The Chinese Government Scholarship for international master's students in China is fully funded by the "
        "government and covers tuition and a monthly stipend. Application deadline: 30 April 2099. How to apply: "
        "submit your application online. Eligibility: non-Chinese citizens with a bachelor's degree. Cybersecurity applicants welcome.")


def _run(pages, cands, otype="Scholarship", countries=("China", "South Korea", "United Kingdom"), level="Master's",
         fields=("Cybersecurity",), roles=()):
    class Fake(BaseSource):
        name = "Fake"

        async def search(self, q, t=None, c=None):
            return [x.model_copy(deep=True) for x in cands]

    async def fake_page(url, timeout=5, max_chars=30000):
        if url in pages:
            v = pages[url]
            return v if isinstance(v, dict) else {"text": v}
        return {}

    real_page, real_mgr = dp.fetch_page, ds.default_source_manager
    dp.fetch_page = fake_page
    ds.default_source_manager = lambda: SourceManager([Fake()])
    try:
        return ds.search_opportunities("", otype, list(roles), list(countries), list(fields), {}, level)[0]
    finally:
        dp.fetch_page, ds.default_source_manager = real_page, real_mgr


def _cand(url, title, **kw):
    return Opportunity(title=title, organization=kw.pop("org", "org"), opportunity_type="SCHOLARSHIP", description="snippet",
                       application_url=url, source_url=url, **kw)


def test_screenshot_scenario_only_real_current_scholarships_survive():
    pages = {
        "https://www.csc.cn/gov-scholarship": GOOD,
        "https://www.csc.cn/old": GOOD.replace("30 April 2099", "30 April 2020"),
        "https://www.tsinghua.edu.cn/guest": "Faculty and guest speakers of the school. Scholarship news. Apply now. China.",
        "https://www.humboldt-foundation.de/postdoc": "Humboldt postdoctoral fellowships fund postdoctoral researchers in Germany and China. Apply now, deadline 1 May 2099. Eligibility.",
        "https://www.asu.edu/db": "Scholarship database of national scholarships and fellowships. Apply now. China. Deadline: 1 May 2099.",
        "https://boren.example.org/select": "The Boren Awards fund the intensive study of language abroad by U.S. students. Eligibility. Apply. China. Deadline: 1 May 2099.",
        "https://jobs.example.com/pm": ("Product Manager. Responsibilities: lead the roadmap. We are looking for a PM. What we offer: salary, "
                                        "full-time. Scholarships and grants for staff. Apply now. China. Deadline: 1 May 2099."),
        "https://akf.example.org/scholarship": "Aga Khan Foundation International Scholarship Programme for master's students. Apply now. Deadline: 1 May 2099. Eligibility.",
    }
    cands = [_cand("https://www.csc.cn/gov-scholarship", "Chinese Government Scholarship Application (Academic Year 2026/2027)_Embassy of the People's Republic of China in the United States of America"),
             _cand("https://www.csc.cn/old", "Old Chinese Government Scholarship"),
             _cand("https://www.tsinghua.edu.cn/guest", "Faculty & Guest Speakers"),
             _cand("https://www.humboldt-foundation.de/postdoc", "Humboldt Postdoc Fellowships"),
             _cand("https://www.asu.edu/db", "Scholarship Database"),
             _cand("https://boren.example.org/select", "Selecting an Eligible Study Program"),
             _cand("https://jobs.example.com/pm", "Product Manager"),
             _cand("https://akf.example.org/scholarship", "Aga Khan Foundation International Scholarship Programme")]
    # a job-board record that a buggy source returned for a scholarship search
    cands.append(build_job("Arbeitnow", "JOB", "1", "QA Engineer Mobile", "ScholarshipOwl", "Berlin", "https://www.arbeitnow.com/jobs/qa",
                           "x" * 200, datetime.now(timezone.utc).timestamp()))
    results = _run(pages, cands)
    assert [r.application_url for r in results] == ["https://www.csc.cn/gov-scholarship"]
    r = results[0]
    assert "_Embassy" not in r.title
    assert r.deadline == "30 April 2099"
    assert "fully funded" in (r.funding or "").lower()
    assert r.metadata["availability"] == "confirmed-open"
    assert r.metadata.get("detected_level") and "Master's" in r.metadata["detected_level"]


def test_without_country_filter_global_scholarship_is_kept_but_wrong_level_is_not():
    pages = {"https://akf.example.org/s": "Aga Khan Foundation International Scholarship Programme for master's students. Apply now. Deadline: 1 May 2099. Eligibility.",
             "https://x.example.org/phd": "PhD scholarship for doctoral candidates. Apply now. Deadline: 1 May 2099. Eligibility."}
    cands = [_cand("https://akf.example.org/s", "Aga Khan Foundation International Scholarship Programme"),
             _cand("https://x.example.org/phd", "PhD Scholarship in Cybersecurity")]
    res = _run(pages, cands, countries=())
    assert [r.application_url for r in res] == ["https://akf.example.org/s"]


def test_unreachable_and_expired_json_ld_pages_are_never_shown():
    pages = {"https://a.example.org/s": {"text": GOOD, "valid_through": "2020-01-01T00:00"}}
    cands = [_cand("https://a.example.org/s", "Chinese Government Scholarship"), _cand("https://dead.example.org/404", "Dead Scholarship")]
    assert _run(pages, cands) == []


def test_job_search_drops_stale_postings_and_keeps_fresh_ones():
    now = datetime.now(timezone.utc)
    fresh = build_job("Arbeitnow", "JOB", "f", "Security Engineer", "Acme", "Berlin, Germany", "https://www.arbeitnow.com/jobs/f",
                      "Responsibilities and requirements for a security engineer role. " * 5, int((now - timedelta(days=3)).timestamp()))
    stale = build_job("Arbeitnow", "JOB", "s", "Security Analyst", "Old Co", "Berlin, Germany", "https://www.arbeitnow.com/jobs/s",
                      "Responsibilities and requirements for a security analyst role. " * 5, int((now - timedelta(days=120)).timestamp()))
    res = _run({}, [fresh, stale], otype="Job", countries=(), level="Any", fields=(), roles=("Security Engineer",))
    assert [r.title for r in res] == ["Security Engineer"]


def test_scholarship_search_rejects_every_job_board_record():
    job = build_job("Remotive", "JOB", "9", "Security Engineer", "Acme", "Worldwide", "https://remotive.com/j/9", "x" * 300,
                    datetime.now(timezone.utc).timestamp())
    assert _run({}, [job], countries=()) == []


def test_relevance_gate_country_alias_and_tld():
    item = Opportunity(title="Study in the UK Scholarship", organization="X", opportunity_type="SCHOLARSHIP",
                       application_url="https://www.ox.ac.uk/scholarship", source_url="https://www.ox.ac.uk/scholarship")
    assert relevance_gate(item, "Scholarship", "Funding for international master's students. Apply now.", ["United Kingdom"], "Master's")[0]
    assert not relevance_gate(item, "Scholarship", "Funding for international master's students. Apply now.", ["Japan"], "Master's")[0]
