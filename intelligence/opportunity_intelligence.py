import re
from datetime import datetime, timezone

NA = "N/A"


def _clean(value):
    text = str(value or "")
    # Convert common HTML markup from job-board pages into readable text.
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(?:p|div|li|h[1-6]|ul|ol)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _first(patterns, text):
    for pattern in patterns:
        m = re.search(pattern, text, re.I | re.S)
        if m:
            return _clean(m.group(1)) if m.groups() else _clean(m.group(0))
    return None


def _contains_any(text, terms):
    low = (text or "").lower()
    return any(t in low for t in terms)


def _segment(text, start_terms, end_terms, max_chars=5000):
    """Extract a semantic section even when the source is flattened to one line."""
    source = _clean(text)
    low = source.lower()
    starts = sorted((low.find(term.lower()), term) for term in start_terms if low.find(term.lower()) >= 0)
    if not starts:
        return ""
    start_pos, start_term = starts[0]
    start = start_pos + len(start_term)
    ends = [low.find(term.lower(), start) for term in end_terms if low.find(term.lower(), start) >= 0]
    end = min(ends) if ends else min(len(source), start + max_chars)
    return source[start:end].strip(" :-–—")


def _has_explicit_detail(value):
    return value not in (None, "", NA, [NA])


def _section(text, headings, stop_headings, max_chars=6000):
    lines = [x.strip() for x in (text or "").splitlines() if x.strip()]
    starts = {h.lower().rstrip(":") for h in headings}
    stops = {h.lower().rstrip(":") for h in stop_headings}
    start = None
    for i, line in enumerate(lines):
        if line.lower().rstrip(":") in starts:
            start = i + 1
            break
    if start is None:
        return ""
    out = []
    for line in lines[start:]:
        if line.lower().rstrip(":") in stops:
            break
        out.append(line)
        if len("\n".join(out)) >= max_chars:
            break
    return "\n".join(out)


def _unique(values):
    out, seen = [], set()
    for value in values:
        value = _clean(value)
        key = value.lower()
        if value and key not in seen:
            seen.add(key)
            out.append(value)
    return out


def _lines_matching(text, patterns, limit=20):
    found = []
    for line in (text or "").splitlines():
        line = _clean(line)
        if not line:
            continue
        if any(re.search(p, line, re.I) for p in patterns):
            found.append(line[:300])
    return _unique(found)[:limit]


def _classify_compensation(text):
    low = (text or "").lower()
    if re.search(r"\b(unpaid|without pay|no compensation)\b", low):
        return "UNPAID"
    if re.search(r"\b(paid internship|paid intern|paid position|competitive salary|competitive stipend)\b", low):
        return "PAID"
    money = re.search(
        r"(?:(?:€|\$|£)\s?[\d,.]+|[\d,.]+\s?(?:€|\$|£))"
        r"(?:\s*(?:per|/|a)\s*(?:month|year|hour|week))?",
        text or "",
        re.I,
    )
    if money:
        return "PAID"
    return NA


def extract_opportunity_details(opportunity):
    text = _clean(opportunity.description)
    low = text.lower()
    meta = dict(opportunity.metadata or {})

    # Compensation: never turn "not specified" into a fake value.
    explicit_missing_comp = _contains_any(low, [
        "salary information is not provided",
        "salary information is unavailable",
        "salary information is not available",
        "salary is not specified",
        "salary not specified",
        "salary is not provided",
        "salary not provided",
        "compensation is not specified",
        "compensation not specified",
        "compensation is not provided",
        "stipend is not specified",
        "stipend not specified",
        "no salary information",
        "no salary is provided",
    ])

    compensation = _first([
        r"(?:salary|pay|compensation|remuneration|stipend|monthly stipend|annual salary)\s*[:\-–]?\s*([^\n.;]{2,120})",
        r"((?:€|\$|£|usd|eur|gbp|pkr)\s?[\d,.]+(?:\s*(?:per|/|a)\s*(?:month|year|hour|week))?)",
        r"([\d,.]+\s*(?:€|\$|£)\s*(?:per|/|a)\s*(?:month|year|hour|week))",
    ], text)

    opportunity.compensation_status = NA if explicit_missing_comp else _classify_compensation(text)
    opportunity.compensation = NA if explicit_missing_comp or not compensation else compensation

    opportunity.duration = _first([
        r"(?:duration|for a period of|lasting)\s*[:\-]?\s*([^\n.;]{2,100})",
        r"(\d+\s*(?:weeks?|months?|years?)(?:\s*(?:internship|placement|program))?)",
    ], text) or NA

    if _contains_any(low, ["fully remote", "100% remote", "remote position", "work remotely", "remote work"]):
        opportunity.work_mode = "Remote"
    elif _contains_any(low, ["hybrid", "partly remote"]):
        opportunity.work_mode = "Hybrid"
    elif _contains_any(low, ["on-site", "onsite", "in office", "office-based"]):
        opportunity.work_mode = "On-site"
    else:
        opportunity.work_mode = NA

    opportunity.application_fee = _first([
        r"(?:application fee|application fees|fee to apply)\s*[:\-]?\s*([^\n.;]{1,100})",
    ], text) or NA

    opportunity.deadline = opportunity.deadline or (_first([
        r"(?:application )?deadline\s*[:\-]?\s*([^\n.;]{2,100})",
        r"(?:apply by|applications close|closing date)\s*[:\-]?\s*([^\n.;]{2,100})",
    ], text) or NA)

    opportunity.tuition = opportunity.tuition or (_first([
        r"(?:tuition|tuition fee|fees)\s*[:\-]?\s*([^\n.;]{2,120})",
    ], text) or NA)

    opportunity.funding = opportunity.funding or (_first([
        r"(?:funding|funded|scholarship|financial support|stipend)\s*[:\-]?\s*([^\n.;]{2,140})",
    ], text) or NA)

    # Structured requirement categories.
    # Job-board HTML is often flattened into one long paragraph. Prefer semantic
    # sections before falling back, and never use the entire description as every field.
    req_section = _segment(
        text,
        ["requirements", "qualifications", "what we're looking for",
         "what we are looking for", "your profile", "essential skills",
         "who you are"],
        ["responsibilities", "your tasks", "what you will do", "what you'll do",
         "beneficial skills", "benefits", "what we offer", "about us", "how to apply"],
        6500,
    )

    education_section = _segment(
        text,
        ["academic background", "education", "degree"],
        ["programming fundamentals", "experience", "testing fundamentals",
         "essential skills", "beneficial skills", "responsibilities",
         "what we offer", "about us", "how to apply"],
        1800,
    )
    experience_section = _segment(
        text,
        ["experience", "professional experience", "consulting experience"],
        ["beneficial skills", "essential skills", "responsibilities",
         "what we offer", "about us", "how to apply"],
        1800,
    )
    language_section = _segment(
        text,
        ["languages", "language requirements"],
        ["teamwork", "what we offer", "about us", "how to apply"],
        1200,
    )
    eligibility_section = _segment(
        text,
        ["eligibility", "nationality", "work authorization", "visa"],
        ["requirements", "qualifications", "responsibilities", "what we offer",
         "about us", "how to apply"],
        1600,
    )

    education = _lines_matching(education_section or req_section, [
        r"\b(?:bachelor|master|phd|doctorate|degree|university|computer science|software engineering|engineering|related field|enrolled|student)\b"
    ])
    experience = _lines_matching(experience_section or req_section, [
        r"\b\d+\+?\s*(?:years?|yrs?)\b.*\bexperience\b",
        r"\b(?:experience|entry[- ]level|recent graduate|enrolled student|student)\b",
    ])
    languages = _lines_matching(language_section or req_section, [
        r"\b(?:english|german|french|spanish|italian|dutch|arabic|chinese|japanese)\b.*\b(?:fluent|proficien|language|spoken|written|level)\b",
        r"\b(?:fluent|proficient|business-fluent|language proficiency|spoken|written)\b",
    ])
    nationality = _lines_matching(eligibility_section or "", [
        r"\bnationality\b", r"\bcitizen(?:ship)?\b", r"\bvisa\b",
        r"\bwork authorization\b", r"\beligib(?:le|ility)\b",
    ])
    documents = _lines_matching(text, [
        r"\b(?:cv|resume|cover letter|transcript|recommendation letter|portfolio|statement of purpose|sop|writing sample)\b.*\b(?:required|submit|upload|application)\b",
        r"\b(?:required documents|application documents)\b",
    ])

    tests = []
    for test in ("IELTS", "TOEFL", "PTE", "GRE", "GMAT", "SAT",
                 "Duolingo English Test", "TestDaF", "DSH"):
        if re.search(r"\b" + re.escape(test) + r"\b", text, re.I):
            tests.append(test)

        # Benefits are only pulled from a benefits/offer section.
    benefit_section = _section(
        text,
        ["benefits", "what we offer", "we offer", "what's in it for you", "what's in for you"],
        ["requirements", "qualifications", "about us", "responsibilities", "how to apply"],
        4000,
    )
    benefits = []
    for line in benefit_section.splitlines():
        line = _clean(line)
        if len(line) >= 4:
            benefits.append(line[:220])

    opportunity.education_requirements = education or [NA]
    opportunity.experience_requirements = experience or [NA]
    opportunity.language_requirements = languages or [NA]
    opportunity.test_requirements = _unique(tests) or [NA]
    opportunity.nationality_restrictions = nationality or [NA]
    opportunity.required_documents = documents or [NA]
    opportunity.benefits = _unique(benefits)[:10] or [NA]

    # Keep the raw description clean, but expose categorized intelligence to UI.
    meta["structured_details"] = {
        "education": opportunity.education_requirements,
        "experience": opportunity.experience_requirements,
        "languages": opportunity.language_requirements,
        "tests": opportunity.test_requirements,
        "nationality": opportunity.nationality_restrictions,
        "documents": opportunity.required_documents,
        "benefits": opportunity.benefits,
        "compensation": opportunity.compensation,
        "compensation_status": opportunity.compensation_status,
        "duration": opportunity.duration,
        "work_mode": opportunity.work_mode,
        "deadline": opportunity.deadline or NA,
        "tuition": opportunity.tuition or NA,
        "funding": opportunity.funding or NA,
        "application_fee": opportunity.application_fee or NA,
    }
    meta["detail_extraction"] = {
        "method": "deterministic_source_text_extraction",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "fields_not_stated_are_na": True,
        "evidence_note": "N/A means the available source text did not state the value. It does not mean the condition does not exist.",
    }
    # Concise source-grounded summary for the UI. No new facts are invented.
    desc_clean = _clean(opportunity.description)
    summary_sentences = re.split(r"(?<=[.!?])\s+", desc_clean)
    summary_sentences = [s.strip() for s in summary_sentences if len(s.strip()) > 25]
    # Keep the overview genuinely short. Detailed source text remains behind the
    # full-description expander.
    meta["summary"] = " ".join(summary_sentences[:2])[:650] if summary_sentences else desc_clean[:650]
    opportunity.metadata = meta
    return opportunity


async def enhance_opportunity_with_llm(opportunity):
    """Translate and semantically structure a discovered opportunity when an LLM is available."""
    import json
    from llm.manager import LLMManager

    manager = LLMManager()
    if not manager.has_external_provider:
        return opportunity

    current = {
        "title": opportunity.title,
        "organization": opportunity.organization,
        "description": opportunity.description or "",
        "requirements": opportunity.requirements,
        "deadline": opportunity.deadline,
        "funding": opportunity.funding,
        "tuition": opportunity.tuition,
        "compensation": opportunity.compensation,
        "application_fee": opportunity.application_fee,
    }
    prompt = f"""
Convert the opportunity information below into clear English and extract only supported facts.
Return JSON only with: title, organization, description, country, city, deadline, funding, tuition,
compensation, compensation_status, application_fee, education_requirements, experience_requirements,
language_requirements, test_requirements, nationality_restrictions, required_documents, benefits,
work_mode, duration, required_skills, verification_notes.

Rules:
- Translate non-English meaning into natural English.
- Do not invent or infer missing values. Use empty string/list for unsupported fields.
- Keep numbers, currencies, dates, requirements and conditions faithful to the source.
- required_skills must contain only skills explicitly required or clearly stated as qualifications.
- This is extraction, not an eligibility judgment.

SOURCE URL: {opportunity.source_url or opportunity.application_url or ''}
SOURCE TEXT:
{(opportunity.description or '')[:18000]}

CURRENT STRUCTURE:
{json.dumps(current, ensure_ascii=False)}
"""
    try:
        raw = await manager.generate(prompt, "You are a careful multilingual opportunity-data extractor. Return valid JSON only.")
        start, end = raw.find("{"), raw.rfind("}")
        if start < 0 or end <= start:
            return opportunity
        data = json.loads(raw[start:end + 1])
    except Exception:
        return opportunity

    def pick_text(key, current_value=None):
        value = data.get(key)
        return str(value).strip() if value not in (None, "") else current_value

    for field in ("title", "organization", "description", "country", "city", "deadline", "funding",
                  "tuition", "compensation", "compensation_status", "application_fee", "work_mode", "duration"):
        value = pick_text(field, getattr(opportunity, field, None))
        if value not in (None, ""):
            setattr(opportunity, field, value)

    for field in ("education_requirements", "experience_requirements", "language_requirements",
                  "test_requirements", "nationality_restrictions", "required_documents", "benefits"):
        value = data.get(field)
        if isinstance(value, list) and value:
            setattr(opportunity, field, _unique(value))

    meta = dict(opportunity.metadata or {})
    skills = data.get("required_skills")
    if isinstance(skills, list) and skills:
        meta["required_skills"] = _unique(skills)
    meta["llm_enhanced"] = True
    meta["translation"] = "English"
    meta["llm_verification_note"] = data.get("verification_notes", "")
    meta["structured_details"] = {
        "education": opportunity.education_requirements,
        "experience": opportunity.experience_requirements,
        "languages": opportunity.language_requirements,
        "tests": opportunity.test_requirements,
        "nationality": opportunity.nationality_restrictions,
        "documents": opportunity.required_documents,
        "benefits": opportunity.benefits,
        "compensation": opportunity.compensation,
        "compensation_status": opportunity.compensation_status,
        "duration": opportunity.duration,
        "work_mode": opportunity.work_mode,
        "deadline": opportunity.deadline,
        "tuition": opportunity.tuition,
        "funding": opportunity.funding,
        "application_fee": opportunity.application_fee,
    }
    opportunity.metadata = meta
    return opportunity
