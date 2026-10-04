"""Link extraction (rules + grounded LLM), scholarship catalogue and per-visitor sessions."""
import asyncio

from intelligence.link_extractor import (
    content_text, details_block, extract_opportunity, merge_llm, parse_llm_json, rule_extract,
)
from intelligence.scholarship_catalog import catalog_options, filter_catalog, load_catalog

URL = "https://isaca.secure-platform.com/a/page/ISACAfoundation/usscholarships/VARTEQ"
TEXT = ("[Skip to Content] Login to Complete a Nomination or to Access the Judging Panel Cybersecurity Scholarship sponsored by "
        "VARTEQ Continue your education and launch your IT career with ISACA! This scholarship is open to students pursuing a "
        "master's degree in cybersecurity at a school in Illinois, United States, or Ukraine. Create a free ISACA account to apply. "
        "Applications Due: 11:59 pm US CT, 3 November 2026 Scholarship Offering: We will award a US$2,500 academic scholarship "
        "to four (4) students. Eligibility: Be 18 years of age or older. Follow Us Facebook Twitter LinkedIn")
PAGE = {"title": "ISACA - About ISACA Foundation Scholarships", "site": "About ISACA Foundation Scholarships",
        "h1": "Cybersecurity Scholarship sponsored by VARTEQ", "text": TEXT}


class FakeLLM:
    has_external_provider = True

    def __init__(self, reply=None, fail=False):
        self.reply, self.fail = reply, fail

    async def generate_external(self, prompt, system=""):
        if self.fail:
            raise RuntimeError("down")
        return self.reply


def test_content_starts_at_the_page_heading_and_drops_chrome():
    text = content_text(PAGE)
    assert text.startswith("Cybersecurity Scholarship sponsored by VARTEQ")
    assert "Login to Complete" not in text and "Follow Us" not in text


def test_rules_use_heading_not_generic_site_title_and_find_facts():
    info = rule_extract(PAGE, URL)
    assert info["title"] == "Cybersecurity Scholarship sponsored by VARTEQ"
    assert info["organization"] == "ISACA"          # not "About ISACA Foundation Scholarships"
    assert info["deadline"] == "3 November 2026"
    assert "US$2,500" in info["funding"]
    assert info["kind"] == "Scholarship"


def test_job_page_gets_company_not_job_title_as_organization():
    page = {"title": "Data Engineer - Acme Corp | Careers", "site": "", "h1": "Data Engineer",
            "text": "Data Engineer Berlin Full-time Salary: €65,000 - €80,000 per year Responsibilities: pipelines. Apply by 15 December 2026."}
    info = rule_extract(page, "https://careers.acme.com/jobs/1")
    assert info["organization"] == "Acme Corp" and info["kind"] == "Job"
    assert info["deadline"] == "15 December 2026" and "65,000" in info["funding"]


def test_llm_fields_are_grounded_in_the_page():
    reply = ('{"title":"Cybersecurity Scholarship sponsored by VARTEQ","organization":"ISACA Foundation","kind":"Scholarship",'
             '"deadline":"3 November 2026","funding":"US$2,500","eligibility":["Be 18 years of age or older","Must hold a PhD in astrology"],'
             '"summary":"US$2,500 award for four IT students."}')
    info = asyncio.run(extract_opportunity(PAGE, URL, FakeLLM(reply)))
    assert info["used_llm"] and info["organization"] == "ISACA Foundation"
    assert info["eligibility"] == ["Be 18 years of age or older"]      # invented requirement dropped
    assert info["summary"].startswith("US$2,500")


def test_llm_cannot_invent_deadline_or_amount():
    merged = merge_llm(rule_extract(PAGE, URL), {"deadline": "1 January 2030", "funding": "US$99,999"}, content_text(PAGE), URL)
    assert merged["deadline"] == "3 November 2026" and "99,999" not in merged["funding"]


def test_llm_failure_or_no_provider_falls_back_to_rules():
    assert asyncio.run(extract_opportunity(PAGE, URL, FakeLLM(fail=True)))["used_llm"] is False
    assert asyncio.run(extract_opportunity(PAGE, URL, FakeLLM("not json")))["used_llm"] is False
    assert asyncio.run(extract_opportunity(PAGE, URL, None))["title"].startswith("Cybersecurity")
    assert parse_llm_json("```json\n{\"a\": 1}\n```") == {"a": 1}


def test_details_block_is_structured():
    block = details_block(rule_extract(PAGE, URL), URL)
    assert "Deadline: 3 November 2026" in block and block.endswith(f"Source: {URL}")


def test_catalog_is_large_categorised_and_filterable():
    rows = load_catalog()
    assert len(rows) >= 50
    opts = catalog_options(rows)
    assert len(opts["categories"]) >= 5 and "Global" in opts["countries"]
    assert filter_catalog(rows, "daad")
    german_masters = filter_catalog(rows, countries=["Germany"], level="Master's")
    assert german_masters and all(r["country"] == "Germany" for r in german_masters)
    assert len({(r["website"] or r["name"]).casefold() for r in rows}) > len(rows) * 0.9   # deduplicated


def test_private_mode_flag(monkeypatch):
    from core import session
    monkeypatch.setenv("PRIVATE_SESSIONS", "1")
    assert session.private_mode() is True
    monkeypatch.setenv("PRIVATE_SESSIONS", "0")
    assert session.private_mode() is False


def test_guest_users_are_isolated_and_purged(tmp_path, monkeypatch):
    import database.db as db
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    db.initialize_database()
    a, b = db.create_guest_user("aaa"), db.create_guest_user("bbb")
    assert a != b and a > 1
    db.save_profile(a, '{"full_name": "A"}')
    assert db.load_profile(b) == "{}" and "A" in db.load_profile(a)
    conn = db.get_connection()
    conn.execute("UPDATE users SET created_at = datetime('now','-5 days') WHERE id=?", (a,))
    conn.commit(); conn.close()
    assert db.purge_old_guests(days=2) == 1
    assert db.load_profile(a) == "{}" and db.get_connection().execute("SELECT id FROM users WHERE id=?", (b,)).fetchone()
