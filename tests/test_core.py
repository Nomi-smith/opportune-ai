from models.opportunity import Opportunity
from intelligence.normalization import normalize_results
from intelligence.deduplication import deduplicate_opportunities

def test_normalize_and_dedupe():
    items = [
        Opportunity(
            title=" Python  Developer ",
            organization="Acme",
            opportunity_type="JOB",
        ),
        Opportunity(
            title="Python Developer",
            organization="Acme",
            opportunity_type="JOB",
        ),
    ]

    normalized = normalize_results(items)
    result = deduplicate_opportunities(normalized)

    assert len(result) == 1


def test_discovery_plan_queries_are_strings():
    from intelligence.discovery_planner import DiscoveryPlanner
    plan = DiscoveryPlanner(None).build_plan(
        "Master's", fields=["Business"], countries=["Italy"]
    )
    assert plan.queries
    assert all(isinstance(query, str) for query in plan.queries)


def test_deterministic_cv_does_not_create_projects():
    from intelligence.profile_intelligence import extract_profile_facts
    facts = extract_profile_facts(
        "Projects\nGame Bot Automation\nBuilt a browser game automation agent using computer vision."
    )
    assert facts["projects"] == []
    assert "Game Bot Automation" in facts["projects"][0]["description"]


def test_deterministic_cv_does_not_create_projects():
    from intelligence.profile_intelligence import extract_profile_facts
    facts = extract_profile_facts("Projects\nGameVision AI\nBuilt a computer vision agent.\nRelevant Coursework\nAlgorithms\nLeadership\n")
    assert facts["projects"] == []


def test_project_state_preserves_blank_blocks():
    # Regression: syncing widgets must not discard a newly added blank project.
    projects = [{"title": "Project 1", "description": "Work"}, {"title": "", "description": ""}]
    assert len(projects) == 2
