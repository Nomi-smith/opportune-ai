import re

from intelligence.skill_taxonomy import extract_skills, merge_skills, normalize_text


def _section(text: str, headings: list[str], max_lines: int = 80) -> str:
    lines = [x.strip() for x in (text or '').splitlines() if x.strip()]
    wanted = {h.lower() for h in headings}
    start = None
    for i, line in enumerate(lines):
        clean = line.lower().rstrip(':').strip()
        if clean in wanted:
            start = i + 1
            break
    if start is None:
        return ''
    out = []
    stop = {
        'skills', 'technical skills', 'education', 'experience', 'work experience',
        'projects', 'certifications', 'awards', 'research', 'publications', 'summary',
        'languages', 'interests', 'references'
    } - wanted
    for line in lines[start:start + max_lines]:
        if line.lower().rstrip(':').strip() in stop:
            break
        out.append(line)
    return '\n'.join(out)


def _clean_project_title(value: str) -> str:
    value = re.sub(r'^[•*▪◦\-–—\d.)\s]+', '', value or '').strip()
    return re.sub(r'\s+', ' ', value)[:180]


def _project_key(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', normalize_text(value)).strip()


def _extract_project_blocks(text: str) -> list[dict]:
    """Projects are intentionally not inferred by deterministic parsing.

    CV sections such as coursework, leadership and freelance experience are too
    ambiguous to classify safely without semantic understanding. LLM extraction
    can be enabled later and must remain evidence-grounded.
    """
    return []

def _merge_projects(existing: list, detected: list[dict]) -> list[dict]:
    result = []
    seen = set()

    for item in existing or []:
        if isinstance(item, str):
            item = {'title': item[:120], 'description': item}
        if not isinstance(item, dict):
            continue
        title = str(item.get('title', '')).strip()
        desc = str(item.get('description', '')).strip()
        if not title and not desc:
            continue
        key = _project_key(title or desc[:120])
        if key and key not in seen:
            result.append({'title': title, 'description': desc})
            seen.add(key)

    for item in detected or []:
        title = str(item.get('title', '')).strip()
        desc = str(item.get('description', '')).strip()
        if not title and not desc:
            continue
        key = _project_key(title or desc[:120])
        if key and key not in seen:
            result.append({'title': title, 'description': desc})
            seen.add(key)

    return result


def extract_profile_facts(cv_text: str) -> dict:
    text = cv_text or ''
    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    education = _section(text, ['education', 'academic background', 'education background'])
    experience = _section(text, ['experience', 'work experience', 'professional experience'])
    projects = _section(text, ['projects', 'academic projects', 'selected projects'])
    # Project structure extraction is intentionally deferred to the LLM layer.
    # Deterministic CV parsing must not turn coursework, skills, leadership,
    # freelance experience, or other CV sections into fake project blocks.
    project_blocks = []
    skills = extract_skills(text)
    return {
        'email': email_match.group(0) if email_match else '',
        'education_text': education,
        'education': education,
        'experience': experience,
        'projects_text': projects,
        'projects': project_blocks,
        'skills': skills,
    }


def build_profile_from_cv(cv_text: str, existing_profile: dict | None = None) -> dict:
    profile = dict(existing_profile or {})
    facts = extract_profile_facts(cv_text)

    profile['skills'] = merge_skills(profile.get('skills', []), facts.get('skills', []))
    for key in ('email', 'education_text', 'experience'):
        if not profile.get(key) and facts.get(key):
            profile[key] = facts[key]

    existing_projects = profile.get('projects', [])
    if isinstance(existing_projects, str):
        existing_projects = [{'title': existing_projects[:120], 'description': existing_projects}]
    profile['projects'] = _merge_projects(existing_projects, facts.get('projects', []))
    if not profile.get('projects_text') and facts.get('projects_text'):
        profile['projects_text'] = facts['projects_text']

    if facts.get('education') and not profile.get('education'):
        profile['education'] = [{'raw': facts['education']}]

    sources = dict(profile.get('field_sources', {}))
    for skill in facts.get('skills', []):
        sources[f'skill:{skill}'] = 'Master CV'
    for key in ('email', 'education_text', 'experience', 'projects'):
        if facts.get(key) and not sources.get(key):
            sources[key] = 'Master CV'
    for project in facts.get('projects', []):
        if project.get('title'):
            sources[f"project:{_project_key(project['title'])}"] = 'Master CV'
    profile['field_sources'] = sources
    profile['cv_indexed'] = True
    return profile


def merge_document_into_profile(text: str, existing_profile: dict | None = None, source_label: str = 'Uploaded document') -> dict:
    profile = dict(existing_profile or {})
    facts = extract_profile_facts(text)
    profile['skills'] = merge_skills(profile.get('skills', []), facts.get('skills', []))
    for key in ('email', 'education_text', 'experience'):
        if facts.get(key) and not profile.get(key):
            profile[key] = facts[key]

    existing_projects = profile.get('projects', [])
    if isinstance(existing_projects, str):
        existing_projects = [{'title': existing_projects[:120], 'description': existing_projects}]
    profile['projects'] = _merge_projects(existing_projects, facts.get('projects', []))

    if facts.get('education') and not profile.get('education'):
        profile['education'] = [{'raw': facts['education']}]
    sources = dict(profile.get('field_sources', {}))
    for skill in facts.get('skills', []):
        sources.setdefault(f'skill:{skill}', source_label)
    for key in ('email', 'education_text', 'experience', 'projects'):
        if facts.get(key):
            sources.setdefault(key, source_label)
    for project in facts.get('projects', []):
        if project.get('title'):
            sources.setdefault(f"project:{_project_key(project['title'])}", source_label)
    profile['field_sources'] = sources
    return profile


def missing_core_profile_fields(profile: dict) -> list[str]:
    missing = []
    if not profile.get('full_name'):
        missing.append('full_name')
    if not profile.get('education') and not profile.get('education_text'):
        missing.append('education')
    if not profile.get('skills'):
        missing.append('skills')
    return missing


async def build_profile_from_cv_with_llm(cv_text: str, base_profile: dict | None = None) -> dict:
    """Use an external LLM to improve CV structure while preserving evidence boundaries."""
    import json
    from llm.manager import LLMManager

    manager = LLMManager()
    if not manager.has_external_provider:
        return dict(base_profile or {})

    prompt = f"""
Extract structured career-profile facts from the CV below.
Return JSON only with these keys:
full_name, email, education_text, experience, skills, projects, certifications, languages,
career_interests, study_interests, research_interests

Rules:
- Use ONLY facts explicitly present in the CV.
- Never invent skills, tools, projects, employers, degrees, scores, dates, or interests.
- skills must be a list of explicitly supported skills/tools.
- projects must be objects with title and description.
- Keep project descriptions faithful to the CV.
- If a field is not supported, use an empty string/list.

CV:
{cv_text[:30000]}
"""
    raw = await manager.generate(prompt, "You are a conservative CV information extractor. Return valid JSON only.")
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return dict(base_profile or {})
    data = json.loads(raw[start:end + 1])
    profile = dict(base_profile or {})

    for key in ("full_name", "email", "education_text", "experience"):
        if data.get(key) and not profile.get(key):
            profile[key] = str(data[key]).strip()

    profile["skills"] = merge_skills(profile.get("skills", []), data.get("skills", []))
    for key in ("career_interests", "study_interests", "research_interests", "certifications", "languages"):
        existing = profile.get(key, [])
        if isinstance(existing, str):
            existing = [existing] if existing.strip() else []
        incoming = data.get(key, [])
        if isinstance(incoming, str):
            incoming = [incoming] if incoming.strip() else []
        profile[key] = _unique_list(existing + incoming)

    existing_projects = profile.get("projects", [])
    incoming_projects = data.get("projects", [])
    profile["projects"] = _merge_projects(existing_projects, incoming_projects)

    sources = dict(profile.get("field_sources", {}))
    for skill in data.get("skills", []) or []:
        sources.setdefault(f"skill:{skill}", "Master CV (LLM extraction)")
    for project in incoming_projects or []:
        if isinstance(project, dict) and project.get("title"):
            sources.setdefault(f"project:{_project_key(project['title'])}", "Master CV (LLM extraction)")
    profile["field_sources"] = sources
    profile["cv_indexed"] = True
    profile["cv_llm_enhanced"] = True
    return profile


def _unique_list(values):
    out, seen = [], set()
    for value in values or []:
        value = str(value or "").strip()
        if not value:
            continue
        key = value.casefold()
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out
