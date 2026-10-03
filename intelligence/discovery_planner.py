import asyncio
import re
from dataclasses import dataclass

from intelligence.deduplication import deduplicate_opportunities
from intelligence.freshness import filter_current_opportunities
from intelligence.normalization import normalize_results
from llm.manager import LLMManager
import json


ROLE_OPTIONS = [
    # Technology / data
    "Software Engineer", "Python Developer", "Web Developer", "Backend Developer",
    "Frontend Developer", "Full Stack Developer", "Data Analyst", "Data Scientist",
    "AI Engineer", "Machine Learning Engineer", "Data Engineer", "Cybersecurity Analyst",
    "DevOps Engineer", "Cloud Engineer", "QA Engineer", "Research Assistant",
    # Business / operations
    "Business Analyst", "Project Coordinator", "Project Manager", "Operations Assistant",
    "Sales Executive", "Business Development Associate", "Account Executive",
    "Customer Support Specialist", "Virtual Assistant", "Administrative Assistant",
    "Human Resources Assistant", "Recruitment Assistant", "Finance Assistant",
    "Accounting Assistant", "Marketing Specialist", "Digital Marketing Specialist",
    # Creative / media
    "Graphic Designer", "UI/UX Designer", "Video Editor", "Content Creator",
    "Social Media Manager", "Social Media Specialist", "Copywriter", "Content Writer",
    "Photographer", "Fashion Marketing Assistant", "Communications Officer",
    # Science / education / public sector
    "Researcher", "Research Intern", "Laboratory Assistant", "Teaching Assistant",
    "Teacher", "Public Policy Assistant", "NGO Program Assistant", "Program Coordinator",
    # General discovery
    "Intern", "Graduate Trainee", "Management Trainee", "Entry-Level Position",
]


COUNTRY_OPTIONS = [
    "Germany", "Netherlands", "Sweden", "Finland", "Denmark", "Norway",
    "France", "Italy", "Spain", "Portugal", "Austria", "Switzerland", "Belgium",
    "United Kingdom", "Ireland", "Poland", "Czech Republic", "Hungary", "Türkiye",
    "Romania", "Estonia", "Latvia", "Lithuania", "Greece", "United States",
    "Canada", "Australia", "New Zealand", "Japan", "South Korea", "China",
    "Singapore", "Malaysia", "United Arab Emirates", "Saudi Arabia", "Qatar",
    "Pakistan", "India", "South Africa", "Brazil", "Other / Custom",
]


FIELD_OPTIONS = [
    "Artificial Intelligence", "Computer Science", "Machine Learning", "Data Science",
    "Cybersecurity", "Software Engineering", "Information Technology", "Robotics",
    "Business Administration", "Finance", "Accounting", "Economics", "Marketing",
    "Management", "Entrepreneurship", "Supply Chain Management", "Human Resources",
    "Engineering", "Mechanical Engineering", "Electrical Engineering", "Civil Engineering",
    "Chemical Engineering", "Environmental Engineering", "Architecture", "Urban Planning",
    "International Relations", "Political Science", "Public Policy", "Development Studies",
    "Sociology", "Psychology", "Education", "Journalism", "Communication", "Media Studies",
    "Film", "Graphic Design", "Fashion", "Fine Arts", "Biotechnology", "Biology",
    "Chemistry", "Physics", "Mathematics", "Public Health", "Biomedical Sciences",
    "Nutrition", "Agriculture", "Food Science", "Environmental Science", "Law",
    "Other / Custom",
]



def _clean_list(values):
    out = []
    seen = set()
    for value in values or []:
        value = str(value or "").strip()
        if not value:
            continue
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out


def _csv(value):
    return _clean_list(re.split(r"[,\n]", value or ""))


def _profile_terms(profile):
    profile = profile or {}
    skills = profile.get("skills", [])
    if isinstance(skills, str):
        skills = _csv(skills)
    projects = profile.get("projects", [])
    terms = []
    for skill in skills:
        terms.append(str(skill))
    if isinstance(projects, list):
        for project in projects[:8]:
            if isinstance(project, dict):
                terms.append(project.get("name", ""))
    return _clean_list(terms)


def _default_query(opportunity_type, fields, profile):
    fields = _clean_list(fields)
    field_text = " ".join(fields[:3])
    profile_terms = _profile_terms(profile)
    profile_text = " ".join(profile_terms[:4])

    if opportunity_type == "Master's":
        return f"{field_text or profile_text or 'computer science artificial intelligence'} master's admissions"
    if opportunity_type == "Scholarship":
        return f"fully funded scholarship {field_text or profile_text or 'computer science artificial intelligence'} master's"
    if opportunity_type == "Research":
        return f"research lab professor {field_text or profile_text or 'artificial intelligence machine learning'}"
    if opportunity_type == "Internship":
        return f"{field_text or profile_text or 'AI machine learning software'} internship"
    if opportunity_type == "Job":
        return f"{field_text or profile_text or 'AI machine learning software'} job"
    return field_text or profile_text or "artificial intelligence opportunities"


def _type_matches(item, requested_type):
    if requested_type in (None, "All"):
        return True

    title = (item.title or "").lower()
    text = f"{title} {(item.description or '')[:12000]}".lower()
    kind = (item.opportunity_type or "").upper()

    if requested_type == "Job":
        if kind == "INTERNSHIP":
            return False
        return kind in {"JOB", "UNKNOWN", ""} and not any(x in title for x in ("intern", "working student", "werkstudent", "trainee"))

    if requested_type == "Internship":
        markers = ("intern", "internship", "working student", "werkstudent", "placement", "trainee")
        return any(x in text for x in markers) and not any(x in title for x in ("senior", "lead", "director", "manager"))

    if requested_type == "Master's":
        if kind in {"JOB", "INTERNSHIP"}:
            return False
        return any(x in text for x in (
            "master's", "master’s", "master degree", "master degree program",
            "msc", "m.sc", "graduate program", "graduate programme", "admissions",
            "admission", "degree program", "degree programme"
        ))

    if requested_type == "Scholarship":
        if kind in {"JOB", "INTERNSHIP"}:
            return False
        return any(x in text for x in (
            "scholarship", "fellowship", "grant", "funding", "financial aid",
            "fully funded", "tuition waiver", "stipend"
        ))

    if requested_type == "Research":
        if kind == "RESEARCH":
            return True
        if kind in {"JOB", "INTERNSHIP"}:
            return False
        return any(x in text for x in ("research", "professor", "laboratory", "lab", "phd"))

    return True



async def _llm_expand_queries(opportunity_type, base_query, roles, countries, fields, profile):
    """Generate diverse web-search queries without inventing user facts.

    The LLM is a query planner only; it does not decide that a page is an
    opportunity. Search results still pass through the normal source filters.
    """
    manager = LLMManager()
    if not manager.has_external_provider:
        return []

    profile = profile or {}
    profile_bits = []
    for key in ("education_text", "career_interests", "study_interests", "research_interests"):
        value = profile.get(key)
        if isinstance(value, list):
            value = ", ".join(map(str, value))
        if value:
            profile_bits.append(f"{key}: {value}")
    skills = profile.get("skills", [])
    if skills:
        profile_bits.append("skills: " + ", ".join(map(str, skills[:15])))

    prompt = f"""
Create up to 6 diverse web search queries for an opportunity discovery engine.
Opportunity type: {opportunity_type}
User query: {base_query or 'none'}
Roles: {', '.join(roles) or 'any'}
Fields: {', '.join(fields) or 'any'}
Countries: {', '.join(countries) or 'any'}
Profile context: {' | '.join(profile_bits) or 'none'}

Rules:
- Search the global public web, not one fixed website.
- For Master's use university/program/admission terminology.
- For Scholarship use scholarship/funding/tuition-waiver/government/university terminology.
- For Research use lab/professor/research-group/research-position terminology.
- For Jobs/Internships use role/employer/career terminology.
- Include broad and specific variants.
- Do not invent a degree, skill, country, employer, professor, or scholarship.
- Return JSON only: {{"queries": ["..."]}}
"""
    try:
        raw = await manager.generate(prompt, "You are a precise search-query planner. Return valid JSON only.")
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return []
        data = json.loads(raw[start:end + 1])
        queries = data.get("queries", [])
        if not isinstance(queries, list):
            return []
        return _clean_list(queries)[:6]
    except Exception:
        return []


@dataclass
class DiscoveryPlan:
    opportunity_type: str
    roles: list[str]
    countries: list[str]
    fields: list[str]
    queries: list[str]
    profile: dict | None = None


class DiscoveryPlanner:
    def __init__(self, manager):
        self.manager = manager

    def build_plan(self, opportunity_type, roles=None, countries=None, fields=None, query="", profile=None):
        opportunity_type = opportunity_type or "All"
        roles = _clean_list(roles)
        countries = _clean_list(countries)
        fields = _clean_list(fields)
        query = (query or "").strip()

        if opportunity_type in {"Job", "Internship"}:
            search_terms = roles or ([query] if query else [])
            if not search_terms:
                search_terms = [_default_query(opportunity_type, fields, profile)]
        elif opportunity_type in {"Master's", "Scholarship", "Research"}:
            # Program/field discovery does not require a role name.
            search_terms = ([query] if query else [])
            if fields:
                search_terms = search_terms or [_default_query(opportunity_type, fields, profile)]
            if not search_terms:
                search_terms = [_default_query(opportunity_type, fields, profile)]
        else:
            search_terms = roles or ([query] if query else []) or [_default_query("All", fields, profile)]

        if opportunity_type in {"Master's", "Scholarship", "Research"} and roles:
            search_terms = _clean_list(search_terms + roles)

        if not countries:
            countries = [""]

        # Bias web search toward the current cycle; freshness is still enforced after fetching pages.
        freshness = {
            "Job": "2026 current open hiring",
            "Internship": "2026 current open internship applications",
            "Master's": "2026 2027 current open admissions",
            "Scholarship": "2026 2027 current open scholarship applications",
            "Research": "2026 2027 current open research positions",
        }.get(opportunity_type, "2026 2027 current opportunities")
        search_terms = [f"{q} {freshness}".strip() for q in search_terms]

        # Avoid a huge Cartesian explosion. Multiple selections are still searched in parallel.
        combinations = [(q, c) for q in search_terms for c in countries]
        combinations = combinations[:8]
        return DiscoveryPlan(opportunity_type, roles, _clean_list(countries), fields, [f"{q} | {c or 'Any country'}" for q, c in combinations], profile or {})

    async def run(self, plan: DiscoveryPlan):
        pairs = []
        for entry in plan.queries:
            query, country = entry.split(" | ", 1)
            pairs.append((query, "" if country == "Any country" else country))

        # Add LLM-generated query variants for complex discovery types.
        if plan.opportunity_type in {"Master's", "Scholarship", "Research"}:
            expanded = await _llm_expand_queries(
                plan.opportunity_type,
                plan.queries[0].split(" | ", 1)[0] if plan.queries else "",
                plan.roles,
                [c for c in plan.countries if c],
                plan.fields,
                plan.profile or {},
            )
            if expanded:
                target_countries = [c for c in plan.countries if c] or [""]
                extra = [(q, c) for q in expanded for c in target_countries]
                pairs.extend(extra[:6])

        # Keep discovery broad but bounded. Every query fans out to all sources,
        # so an unbounded Cartesian product would waste API quota.
        unique_pairs = []
        seen_pairs = set()
        for q, c in pairs:
            key = ((q or "").strip().casefold(), (c or "").strip().casefold())
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            unique_pairs.append((q, c))
        pairs = unique_pairs[:8]

        async def one(query, country):
            try:
                return await self.manager.search(
                    query,
                    None if plan.opportunity_type == "All" else plan.opportunity_type,
                    country or None,
                )
            except Exception:
                return []

        batches = await asyncio.gather(*(one(q, c) for q, c in pairs))
        merged = [item for batch in batches for item in batch]
        filtered = [item for item in merged if _type_matches(item, plan.opportunity_type)]
        return filter_current_opportunities(deduplicate_opportunities(normalize_results(filtered)))


async def discover(manager, opportunity_type, roles=None, countries=None, fields=None, query="", profile=None):
    planner = DiscoveryPlanner(manager)
    plan = planner.build_plan(opportunity_type, roles, countries, fields, query, profile)
    return await planner.run(plan)
