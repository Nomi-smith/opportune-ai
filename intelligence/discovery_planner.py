import asyncio
import re
from dataclasses import dataclass

from intelligence.deduplication import deduplicate_opportunities
from intelligence.freshness import filter_current_opportunities, availability_reason
from intelligence.opportunity_quality import quality_filter, annotate_quality, source_tier
from intelligence.opportunity_type import classify_opportunity, page_is_non_actionable, is_aggregate_listing
from intelligence.source_content import extract_deadline, extract_funding
from intelligence.collection_expander import expand_collections
from intelligence.country_sources import preferred_domains
from intelligence.source_registry import domains_for
from intelligence.scholarship_library import seed_queries as scholarship_seed_queries
from sources.webfetch import fetch_url, fetch_page
from intelligence.relevance import relevance_gate, level_label, looks_like_job_posting, is_scholarship_index
from urllib.parse import urlparse
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


STUDY_LEVELS = ["Any", "Bachelor's", "Master's", "PhD"]
RESEARCH_LEVELS = ["Any", "PhD", "Postdoc", "Research Assistant"]
DISCOVERY_TYPES = ["Study / Degree", "Scholarship", "Research", "Job", "Internship"]


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


def _type_matches(item, requested_type, source_text=""):
    accepted, _reason = classify_opportunity(item, requested_type, source_text)
    return accepted


SEARCH_BUDGET = 40      # seconds: stop waiting for slow search lanes and use what has arrived
VERIFY_BUDGET = 30      # seconds for fetching/checking candidate pages
EXPAND_BUDGET = 18      # seconds for crawling catalogue pages
REVIEW_BUDGET = 25      # seconds for the LLM quality review
LANE_CONCURRENCY = 6
MAX_JOB_AGE_DAYS = 45   # a posting older than this is almost always filled: never show it
VERIFY_CONCURRENCY = 20


async def _gather_budget(coros, timeout: float):
    """Run coroutines concurrently; whatever has not finished after `timeout` is cancelled.
    Returns results aligned with the input (None for unfinished or failed)."""
    tasks = [asyncio.ensure_future(c) for c in coros]
    if not tasks:
        return []
    done, pending = await asyncio.wait(tasks, timeout=timeout)
    for t in pending:
        t.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    out = []
    for t in tasks:
        if t in done and not t.cancelled() and t.exception() is None:
            out.append(t.result())
        else:
            out.append(None)
    return out


def _days_old(value) -> int | None:
    from datetime import datetime, timezone
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            stamp = float(text)
            if stamp > 1e11:          # milliseconds
                stamp /= 1000.0
            moment = datetime.fromtimestamp(stamp, tz=timezone.utc)
        else:
            moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if moment.tzinfo is None:
                moment = moment.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - moment).days)
    except Exception:
        return None


def _early_type_ok(item, requested_type: str) -> bool:
    """Cheap, title-level rejection BEFORE any page is fetched (saves the verification budget).

    Keeps a job-board record out of non-job searches and a job-looking title out of
    scholarship / admissions searches, whatever source it came from.
    """
    meta = getattr(item, "metadata", {}) or {}
    structured = bool(meta.get("structured_listing"))
    rt = requested_type
    if rt in {"Job", "Internship"}:
        if structured:
            kind = str(getattr(item, "opportunity_type", "") or "").upper()
            return kind == rt.upper()
        return True
    if structured:
        return False
    if meta.get("library_seed"):
        return True
    title = str(getattr(item, "title", "") or "")
    if rt in {"Scholarship", "Master's", "Study / Degree"} and title and looks_like_job_posting(title, ""):
        return False
    if rt == "Scholarship" and is_scholarship_index(title):
        return False
    return True


_BLANKS = {"", "n/a", "na", "none", "null", "not stated", "unknown", "not found", "see source"}


def _blank(value) -> bool:
    """True for None / '' / 'N/A' ...: normalization stamps 'N/A' into empty fields, which is NOT a real value."""
    return str(value or "").strip().casefold() in _BLANKS


def _json_ld_closed(valid_through: str) -> bool:
    from datetime import date
    from intelligence.freshness import _dates
    days = _dates(valid_through or "")
    return bool(days) and max(days) < date.today()


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
        raw = await manager.generate_external(prompt, "You are a precise search-query planner. Return valid JSON only.")
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
    study_level: str = "Any"
    research_level: str = "Any"


class DiscoveryPlanner:
    def __init__(self, manager):
        self.manager = manager

    def build_plan(self, opportunity_type, roles=None, countries=None, fields=None, query="", profile=None, study_level="Any", research_level="Any"):
        opportunity_type = opportunity_type or "All"
        if opportunity_type == "Study / Degree":
            # Same opportunity family; "Master's" carries the dedicated admissions query lanes.
            opportunity_type = "Master's"
        roles = _clean_list(roles)
        countries = _clean_list(countries)
        fields = _clean_list(fields)
        field_text = " ".join(fields[:3])
        query = (query or "").strip()
        study_level = study_level or "Any"
        research_level = research_level or "Any"

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

        # Build multiple independent lanes PER COUNTRY. A multi-country search must not
        # collapse all countries into one query because that lets search engines return
        # one country and silently ignore the others.
        freshness = {
            "Job": "2026 current open hiring vacancy",
            "Internship": "2026 current open internship placement applications",
            "Master's": "2026 2027 current open master's admissions",
            "Scholarship": "2026 2027 current open scholarship funding applications",
            "Research": "2026 2027 current open research fellowship position",
        }.get(opportunity_type, "2026 2027 current opportunities")

        base = _clean_list(search_terms)
        level_hint = ""
        if opportunity_type in {"Master's", "Scholarship"} and study_level != "Any":
            level_hint = study_level
        elif opportunity_type == "Research" and research_level != "Any":
            level_hint = research_level

        # One search subject ("lane family") per selected field / role, so choosing several
        # fields or roles searches ALL of them instead of only the first few.
        if opportunity_type in {"Job", "Internship"}:
            subjects = base[:5] or [_default_query(opportunity_type, fields, profile)]
            subject_fields = [None] * len(subjects)
        elif fields:
            subjects, subject_fields = [], []
            for f in fields[:6]:
                subjects.append(f"{query} {f}".strip() if query else _default_query(opportunity_type, [f], profile))
                subject_fields.append(f)
        else:
            subjects = [base[0] if base else _default_query(opportunity_type, fields, profile)]
            subject_fields = [None]
        if level_hint:
            subjects = [f"{level_hint} {x}".strip() for x in subjects]

        def lane_templates(q0, subject_field, country_suffix):
            fld = subject_field or q0
            if opportunity_type == "Scholarship":
                return [
                    f"{q0}{country_suffix} {freshness}",
                    f"{q0}{country_suffix} scholarship fellowship grant stipend funding international students",
                    f"{fld}{country_suffix} fully funded tuition waiver financial aid scholarship",
                    f"{q0}{country_suffix} university government scholarship application deadline",
                    f"{fld}{country_suffix} site:edu scholarship international master's students",
                ]
            if opportunity_type == "Master's":
                return [
                    f"{q0}{country_suffix} {freshness}",
                    f"{q0}{country_suffix} university admissions international students",
                    f"{q0}{country_suffix} master's programme application deadline",
                    f"{q0}{country_suffix} official university degree application",
                ]
            if opportunity_type == "Research":
                return [
                    f"{q0}{country_suffix} {freshness}",
                    f"{q0}{country_suffix} professor research group fellowship",
                    f"{q0}{country_suffix} funded research position application",
                    f"{q0}{country_suffix} university research vacancy fellowship",
                ]
            if opportunity_type == "Internship":
                return [
                    f"{q0}{country_suffix} {freshness}",
                    f"{q0}{country_suffix} internship placement international students",
                    f"{q0}{country_suffix} company internship vacancy apply",
                ]
            if opportunity_type == "Job":
                return [
                    f"{q0}{country_suffix} {freshness}",
                    f"{q0}{country_suffix} jobs vacancy careers apply",
                    f"{q0}{country_suffix} employer hiring {q0}",
                ]
            return [f"{q0}{country_suffix} {freshness}"]

        # Lanes are grouped per (country, subject). Groups are then interleaved round-robin
        # under a global cap, so every selected country and every selected field gets coverage
        # and total search time stays bounded however many filters are chosen.
        groups = []
        for country in countries:
            c = country.strip()
            domains = []
            if c:
                for domain in domains_for(c, opportunity_type, limit=12):
                    if domain not in domains:
                        domains.append(domain)
                for domain in preferred_domains(c, opportunity_type):
                    if domain not in domains:
                        domains.append(domain)
            country_suffix = f" {c}" if c else ""
            site_clauses = []
            for start_i in range(0, len(domains), 4):
                chunk = domains[start_i:start_i + 4]
                if chunk:
                    site_clauses.append(" OR ".join(f"site:{d}" for d in chunk))
            for si, (q0, subject_field) in enumerate(zip(subjects, subject_fields)):
                lanes = []
                for qi, template in enumerate(lane_templates(q0, subject_field, country_suffix)):
                    # Official-domain lanes only for the first subject; the broad web lane for all.
                    if site_clauses and si == 0 and qi < 2:
                        lanes.append((f"({site_clauses[0]}) {template}", c))
                    lanes.append((template, c))
                groups.append(lanes)

        # Curated scholarship library seeds (kept small: the library is also fed in directly,
        # keyless, by ScholarshipLibrarySource). Still verified like everything else.
        if opportunity_type == "Scholarship":
            try:
                seed_lanes = []
                for seed_query, seed_country, _seed in scholarship_seed_queries(countries, study_level, fields, limit=8):
                    if seed_country and seed_country not in countries:
                        continue
                    seed_lanes.append((seed_query, seed_country))
                if seed_lanes:
                    groups.append(seed_lanes)
            except Exception:
                pass

        cap = 30 if opportunity_type == "Scholarship" else 24
        seen = set()
        query_pairs = []
        while len(query_pairs) < cap and any(groups):
            for g in groups:
                while g:
                    q, c = g.pop(0)
                    key = (q.casefold().strip(), c.casefold().strip())
                    if key not in seen:
                        seen.add(key)
                        query_pairs.append((q, c))
                        break
                if len(query_pairs) >= cap:
                    break
        return DiscoveryPlan(
            opportunity_type, roles, _clean_list(countries), fields,
            [f"{q} | {c or 'Any country'}" for q, c in query_pairs],
            profile or {}, study_level, research_level
        )

    async def run(self, plan: DiscoveryPlan):
        pairs = []
        for entry in plan.queries:
            query, country_text = entry.split(" | ", 1)
            pairs.append((query, country_text if country_text != "Any country" else ""))

        # LLM query expansion is part of the normal quality pipeline now. It broadens
        # recall; it does not decide acceptance. If the LLM is unavailable, deterministic
        # country/type query lanes continue to work.
        if plan.opportunity_type in {"Master's", "Scholarship", "Research", "Job", "Internship"}:
            try:
                expanded = await asyncio.wait_for(_llm_expand_queries(
                    plan.opportunity_type,
                    plan.queries[0].split(" | ", 1)[0] if plan.queries else "",
                    plan.roles,
                    [c for c in plan.countries if c],
                    plan.fields,
                    plan.profile or {},
                ), timeout=8)
            except Exception:
                expanded = []
            if expanded:
                target_countries = [c for c in plan.countries if c] or [""]
                # At most two LLM-generated variants per country; deterministic
                # registry lanes remain the coverage backbone.
                for country in target_countries:
                    for q in expanded[:2]:
                        pairs.append((q, country))

        unique_pairs = []
        seen_pairs = set()
        for q, c in pairs:
            key = ((q or "").strip().casefold(), (c or "").strip().casefold())
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            unique_pairs.append((q, c))
        if plan.countries:
            balanced_pairs = []
            for country in plan.countries:
                cp = [pair for pair in unique_pairs if pair[1].casefold() == country.casefold()]
                balanced_pairs.extend(cp[:16] if plan.opportunity_type == "Scholarship" else cp[:8])
            pairs = balanced_pairs
        else:
            pairs = unique_pairs[:36]

        lane_gate = asyncio.Semaphore(LANE_CONCURRENCY)

        async def one(query, country_text):
            async with lane_gate:
                try:
                    return await self.manager.search(
                        query,
                        None if plan.opportunity_type == "All" else plan.opportunity_type,
                        country_text or None,
                    )
                except Exception:
                    return []

        batches = await _gather_budget([one(q, c) for q, c in pairs], SEARCH_BUDGET)
        merged = [item for batch in batches if batch for item in batch]
        # Do not trust the source adapter's opportunity_type. It may simply echo the
        # requested search type. Hard classification happens from title/content.
        filtered = [item for item in merged if not page_is_non_actionable(item) and _early_type_ok(item, plan.opportunity_type)]
        items = deduplicate_opportunities(normalize_results(filtered))

        # Preserve canonical catalogue links from the curated library. For catalogue
        # entries such as DAAD, "View source" should open the scholarship database,
        # not a generic homepage. Individual application/source pages remain untouched.
        if plan.opportunity_type == "Scholarship":
            try:
                seeds = scholarship_seed_queries(plan.countries, plan.study_level, plan.fields, limit=48)
                seed_map = {str(seed.get("name", "")).casefold(): seed for _, _, seed in seeds}
                for item in items:
                    title = str(getattr(item, "title", "") or "").casefold()
                    for name, seed in seed_map.items():
                        if name and (name in title or (len(title) >= 8 and title in name)):
                            meta = dict(getattr(item, "metadata", {}) or {})
                            meta["library_seed"] = seed.get("name")
                            meta["library_source_kind"] = seed.get("source_kind")
                            meta["library_source_url"] = seed.get("source_url")
                            item.metadata = meta
                            if seed.get("source_kind") == "catalogue" and seed.get("source_url"):
                                item.application_url = seed["source_url"]
                            break
            except Exception:
                pass

        selected_countries = [c for c in plan.countries if c]
        preferred = []
        for country in selected_countries:
            preferred.extend(preferred_domains(country, plan.opportunity_type))
        preferred = list(dict.fromkeys(preferred))
        preferred_set = {d.lower().replace('www.', '') for d in preferred}

        def host_matches(host, domain):
            host = (host or '').lower().replace('www.', '')
            domain = domain.lower().replace('www.', '')
            return host == domain or host.endswith('.' + domain)

        for item in items:
            meta = dict(getattr(item, 'metadata', {}) or {})
            url = getattr(item, 'application_url', '') or getattr(item, 'source_url', '')
            host = urlparse(url).netloc
            matched = next((d for d in preferred_set if host_matches(host, d)), None)
            meta['country_source_priority'] = 'preferred' if matched else 'web'
            if matched:
                meta['preferred_source_domain'] = matched
                meta['source_tier'] = 'preferred'
            item.metadata = meta

        # First pass: use search-result evidence only to remove obvious historical/closed pages.
        # Unknown candidates are retained temporarily so we can verify their actual webpages
        # instead of incorrectly discarding them because a search snippet omitted a deadline.
        preliminary = []
        for item in items:
            ok, reason = availability_reason(item)
            meta = dict(getattr(item, 'metadata', {}) or {})
            meta['availability_check'] = reason
            item.metadata = meta
            # Unknown status is not a rejection: snippets rarely carry deadlines, and the real page is
            # fetched and checked next. Only explicit closure / a past deadline drops a candidate here.
            if ok or 'no explicit' in reason.casefold() or 'no current/future deadline' in reason.casefold():
                preliminary.append(item)

        annotated_all = [annotate_quality(x) for x in preliminary]
        collection_candidates = [x for x in annotated_all if (getattr(x, 'metadata', {}) or {}).get('page_class') == 'collection'
                                 or (getattr(x, 'metadata', {}) or {}).get('library_source_kind') == 'catalogue']
        annotated = quality_filter(annotated_all, include_unverified=True)

        # Verify only the uncertain top candidates. This runs concurrently and is capped so
        # discovery stays fast. Existing explicit-current candidates do not need another fetch.
        # Fetch enough real source pages to make type decisions from source content.
        # Search snippets are never sufficient to turn a page into a scholarship.
        def _priority(x):
            m = getattr(x, 'metadata', {}) or {}
            return (0 if m.get('structured_listing') else 1,
                    0 if m.get('library_seed') else 1,
                    0 if m.get('country_source_priority') == 'preferred' else 1,
                    0 if m.get('source_tier') in {'official', 'preferred'} else 1)
        # Most trustworthy candidates first, so the verification time budget is spent where it counts.
        uncertain = sorted(annotated, key=_priority)[:150]

        blocked_hosts = {
            'facebook.com', 'instagram.com', 'reddit.com', 'x.com', 'twitter.com',
            'tiktok.com', 'youtube.com', 'medium.com', 'quora.com', 'pinterest.com',
        }

        def blocked_host(host):
            host = (host or '').lower().replace('www.', '')
            return any(host == d or host.endswith('.' + d) for d in blocked_hosts)

        async def verify_one(item):
            url = getattr(item, 'application_url', '') or getattr(item, 'source_url', '')
            if not url:
                return None
            if blocked_host(urlparse(url).netloc):
                meta = dict(getattr(item, 'metadata', {}) or {})
                meta['quality_status'] = 'rejected-social-or-discussion-host'
                item.metadata = meta
                return None
            structured = bool((getattr(item, 'metadata', {}) or {}).get('structured_listing')) and len(str(getattr(item, 'description', '') or '')) > 120

            def reject(status, why=''):
                m = dict(getattr(item, 'metadata', {}) or {})
                m['quality_status'] = status
                if why:
                    m['reject_reason'] = why
                item.metadata = m
                return None

            signals = {}
            if structured:
                # A job-board API record already carries the full posting; no page fetch needed.
                page = str(item.description)
            else:
                signals = await fetch_page(url, timeout=5, max_chars=30000) or {}
                page = signals.get('text', '')
            if not page:
                return None            # unreachable / 404 / not HTML: never shown
            if is_aggregate_listing(item, plan.opportunity_type):
                return reject('rejected-aggregate-listing')
            meta = dict(getattr(item, 'metadata', {}) or {})
            meta['search_snippet'] = meta.get('search_snippet') or getattr(item, 'description', '')
            meta['verification_page_fetched'] = True
            meta['verification_source_url'] = url
            meta['verified_page'] = True
            if signals.get('description'):
                meta['page_description'] = signals['description']
            if signals.get('date_posted') and not meta.get('posted_date'):
                meta['posted_date'] = signals['date_posted']
            item.metadata = meta
            item.description = page

            # The page publishes its own expiry (JSON-LD validThrough): trust it over any guess.
            if _json_ld_closed(signals.get('valid_through', '')):
                return reject('rejected-expired', 'Page marks itself valid only until ' + signals['valid_through'])
            if signals.get('valid_through') and _blank(getattr(item, 'deadline', None)):
                item.deadline = signals['valid_through'][:10]

            # ---- hard type / relevance gates: decided from the page, never from the search snippet
            if not structured:
                accepted, type_reason = classify_opportunity(item, plan.opportunity_type, page)
                meta = dict(getattr(item, 'metadata', {}) or {})
                meta['type_check'] = type_reason
                meta['type_verified'] = accepted
                item.metadata = meta
                if page_is_non_actionable(item, page) or not accepted:
                    return reject('rejected-type', type_reason)
                ok_rel, why_rel = relevance_gate(item, plan.opportunity_type, page, plan.countries,
                                                 plan.study_level, plan.research_level)
                if not ok_rel:
                    return reject('rejected-relevance', why_rel)
                meta = dict(getattr(item, 'metadata', {}) or {})
                lvl = level_label(getattr(item, 'title', ''), page)
                if lvl:
                    meta['detected_level'] = lvl
                item.metadata = meta
            meta = dict(getattr(item, 'metadata', {}) or {})

            # Only populate deadline/funding from actual source content.
            deadline = extract_deadline(page)
            funding = extract_funding(page)
            if deadline and _blank(getattr(item, 'deadline', None)):
                item.deadline = deadline
            if funding and _blank(getattr(item, 'funding', None)):
                item.funding = funding

            # ---- currentness: closed / expired / filled is never shown
            ok, reason = availability_reason(item)
            meta['availability_check'] = reason
            low_reason = str(reason or '').casefold()
            page_low = page.casefold()
            hard_closed = any(token in low_reason for token in (
                'closed', 'expired', 'deadline has passed', 'no longer accepting', 'passed',
            )) or any(token in page_low for token in (
                'applications are closed', 'application is closed', 'deadline has passed',
                'applications have closed', 'no longer accepting applications',
            ))
            if hard_closed:
                return reject('rejected-expired', reason)
            if structured:
                age = _days_old(meta.get('posted_date'))
                if age is not None and age > MAX_JOB_AGE_DAYS:
                    return reject('rejected-stale-listing', f'Posted {age} days ago')
                meta['availability'] = 'posted-recently' if age is not None else 'listed'
                meta['quality_status'] = 'verified-current'
                item.metadata = meta
                return item
            if not structured and plan.opportunity_type in {'Job', 'Internship'}:
                age = _days_old(meta.get('posted_date'))
                if age is not None and age > MAX_JOB_AGE_DAYS:
                    return reject('rejected-stale-listing', f'Posted {age} days ago')

            # A missing/unclear deadline is not the same thing as an expired page: many legitimate
            # programmes run annual rounds. Keep it only when the page itself says how to apply.
            actionable_signal = any(token in page_low for token in (
                'apply now', 'how to apply', 'application deadline', 'application period',
                'apply for the scholarship', 'applications are open', 'open call',
                'submit your application', 'scholarship application', 'funding opportunity',
                'apply online', 'application form', 'eligibility', 'apply by',
            ))
            if not (ok or actionable_signal):
                return reject('rejected-no-evidence-open', reason)
            meta['availability'] = 'confirmed-open' if ok else 'open-deadline-not-stated'
            meta['quality_status'] = 'verified-current'
            item.metadata = meta
            return item

        verify_gate = asyncio.Semaphore(VERIFY_CONCURRENCY)

        async def gated_verify(x):
            async with verify_gate:
                return await verify_one(x)

        verified_batches = await _gather_budget([gated_verify(x) for x in uncertain], VERIFY_BUDGET)
        verified_ids = {id(x) for x in uncertain}
        verified_map = {}
        for original, result in zip(uncertain, verified_batches):
            if not isinstance(result, Exception):
                verified_map[id(original)] = result

        direct = []
        for item in annotated:
            if id(item) in verified_ids:
                checked = verified_map.get(id(item))
                if checked is not None:
                    direct.append(checked)

        # Collection expansion is also verified through the same hard type gate.
        has_catalogue = any((getattr(x, 'metadata', {}) or {}).get('library_source_kind') == 'catalogue' for x in collection_candidates)
        if (len(direct) < 20 or has_catalogue) and plan.opportunity_type in {'Scholarship', "Master's", 'Research'}:
            for x in collection_candidates:
                # Expansion treats these as collection pages whatever the text heuristic said.
                (getattr(x, 'metadata', {}) or {})['page_class'] = 'collection'
            try:
                expanded = await asyncio.wait_for(
                    expand_collections(collection_candidates, plan.opportunity_type, max_pages=10, max_links=40),
                    timeout=EXPAND_BUDGET)
            except Exception:
                expanded = []
            expanded_verified = await _gather_budget([gated_verify(x) for x in expanded[:120]], EXPAND_BUDGET)
            for result in expanded_verified:
                if result is not None and not isinstance(result, Exception):
                    direct.append(result)

        direct = deduplicate_opportunities(direct)

        # Semantic second-stage review: only verified source pages reach the LLM.
        # This intentionally trades some latency for much better opportunity quality.
        try:
            from intelligence.llm_reranker import llm_review
            reviewed = await asyncio.wait_for(llm_review(plan, direct), timeout=REVIEW_BUDGET)
            if reviewed:
                direct = reviewed
        except Exception:
            pass

        rank={'preferred':0,'official':1,'organization':2,'database':3,'web':4}
        direct.sort(key=lambda x: (
            -int((getattr(x,'metadata',{}) or {}).get('llm_quality_score', 0) or 0),
            0 if (getattr(x,'metadata',{}) or {}).get('country_source_priority') == 'preferred' else 1,
            rank.get((getattr(x,'metadata',{}) or {}).get('source_tier'),4),
            (getattr(x,'title','') or '').casefold(),
        ))
        return direct[:50]


async def discover(manager, opportunity_type, roles=None, countries=None, fields=None, query="", profile=None, study_level="Any", research_level="Any"):
    planner = DiscoveryPlanner(manager)
    plan = planner.build_plan(opportunity_type, roles, countries, fields, query, profile, study_level, research_level)
    return await planner.run(plan)
