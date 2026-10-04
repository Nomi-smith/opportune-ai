from models.opportunity import Opportunity
from intelligence.opportunity_type import classify_opportunity
from intelligence.source_content import extract_deadline, extract_funding, clean_source_html


def item(title, desc=""):
    return Opportunity(title=title, organization="Test", opportunity_type="Scholarship", description=desc)


def test_scholarship_accepts_real_funding_page():
    ok, _ = classify_opportunity(item("DAAD Study Scholarship", "Scholarship for international students. Applications open. Deadline: 15 November 2026."), "Scholarship")
    assert ok


def test_scholarship_rejects_internship():
    ok, _ = classify_opportunity(item("Summer Internship 2026", "Internship applications are open for students. Funding may be available."), "Scholarship")
    assert not ok


def test_scholarship_rejects_degree_only():
    ok, _ = classify_opportunity(item("MSc Artificial Intelligence", "Master's degree admissions for 2027."), "Scholarship")
    assert not ok


def test_scholarship_rejects_job():
    ok, _ = classify_opportunity(item("Senior Director - EMEA", "Careers vacancy. Apply now."), "Scholarship")
    assert not ok


def test_degree_accepts_masters():
    ok, _ = classify_opportunity(item("MSc Artificial Intelligence", "Applications are open for the Master's degree program."), "Study / Degree")
    assert ok


def test_clean_source_removes_navigation():
    html = '<header>Skip to content</header><nav>Menu</nav><main><h1>Scholarship</h1><p>Applications open.</p></main><footer>Cookie policy</footer>'
    text = clean_source_html(html)
    assert 'Skip to content' not in text
    assert 'Cookie policy' not in text
    assert 'Scholarship' in text


def test_field_extractors():
    text = 'Scholarship applications close on 15 November 2026. The award provides full tuition waiver and stipend.'
    assert extract_deadline(text)
    assert extract_funding(text)


def test_build_plan_fans_out_selected_countries():
    from intelligence.discovery_planner import DiscoveryPlanner
    planner = DiscoveryPlanner(None)
    plan = planner.build_plan(
        "Scholarship", [], ["Germany", "China", "Türkiye"],
        ["Artificial Intelligence"], "", {}, "Master's", "Any"
    )
    assert len(plan.queries) >= 12
    query_text = " ".join(plan.queries).lower()
    assert "germany" in query_text and "china" in query_text and "türkiye" in query_text


def test_build_plan_does_not_merge_countries_into_one_query():
    from intelligence.discovery_planner import DiscoveryPlanner
    planner = DiscoveryPlanner(None)
    plan = planner.build_plan(
        "Scholarship", [], ["Germany", "China"],
        ["Artificial Intelligence"], "", {}, "Master's", "Any"
    )
    assert any("| Germany" in q for q in plan.queries)
    assert any("| China" in q for q in plan.queries)
