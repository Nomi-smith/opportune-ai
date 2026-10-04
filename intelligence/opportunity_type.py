"""Hard opportunity-type classification for discovery results.

Search engines are discovery layers, not truth. This module classifies a page from
its title + clean source content and applies explicit negative rules so a scholarship
search cannot silently become a job, internship, degree programme, or discussion feed.
"""
from __future__ import annotations
import re

POSITIVE = {
    "Scholarship": (
        r"\bscholarships?\b", r"\bstudy scholarship\b", r"\btuition waiver\b",
        r"\bfinancial aid\b", r"\bfellowships?\b", r"\bstipends?\b", r"\bgrants?\b",
        r"\baward(?:s)? for students\b", r"\bfunding (?:for|to) (?:students|study)\b",
        r"\bfunded (?:master'?s|study|degree|programme|program)\b",
    ),
    "Internship": (
        r"\binternships?\b", r"\bintern\b", r"\bworking student\b", r"\btrainee(?:ship)?\b",
        r"\bplacement\b",
    ),
    "Job": (
        r"\bjob(?:s)?\b", r"\bvacanc(?:y|ies)\b", r"\bcareers?\b", r"\bhiring\b",
        r"\bemployment\b", r"\bposition(?:s)?\b", r"\bapply now\b",
    ),
    "Study / Degree": (
        r"\bmaster'?s? degree\b", r"\bmaster of science\b", r"\bmsc\b", r"\bbachelor'?s? degree\b",
        r"\bundergraduate degree\b", r"\bdegree programme\b", r"\bdegree program\b",
        r"\bgraduate programme\b", r"\bgraduate program\b", r"\badmissions?\b",
        r"\bapply for (?:the )?(?:master|bachelor|degree)\b",
    ),
    "Research": (
        r"\bresearch position\b", r"\bresearch vacancy\b", r"\bresearch assistant\b",
        r"\bdoctoral position\b", r"\bphd position\b", r"\bpostdoc(?:toral)?\b",
        r"\bdoctoral researcher\b", r"\bresearch fellow(?:ship)?\b", r"\bresearch group\b",
    ),
}

NEGATIVE = {
    "Scholarship": (
        r"\binternships?\b", r"\bintern\b", r"\bvacanc(?:y|ies)\b", r"\bhiring\b",
        r"\bemployment\b", r"\bjob openings?\b", r"\bcareer opportunities\b",
        r"\bconference\b", r"\bwebinar\b", r"\bdiscussion\b", r"\bforum\b",
        r"\bnews(?: article)?\b", r"\bblog\b", r"\blist of\b", r"\btop \d+\b",
        r"\bphd (?:position|vacancy|opening)s?\b", r"\bdoctoral (?:position|vacancy|opening)s?\b",
    ),
    "Internship": (r"\bscholarship database\b", r"\bscholarship opportunities\b"),
    "Job": (r"\binternships?\b", r"\bscholarships?\b", r"\bdegree programme\b", r"\bdegree program\b"),
    "Study / Degree": (r"\binternships?\b", r"\bjob vacancy\b", r"\bhiring\b"),
    "Research": (r"\binternships?\b", r"\bjob vacancy\b", r"\bscholarship database\b"),
}

ACTION = (
    r"\bapply\b", r"\bapplication\b", r"\bdeadline\b", r"\bapplications? (?:open|closed)\b",
    r"\baccepting applications\b", r"\bapply by\b", r"\bapplication portal\b",
    r"\bhow to apply\b", r"\beligibility\b", r"\bfunding\b", r"\btuition waiver\b",
)

LEAD = (
    "discussion", "forum", "reddit", "quora", "blog", "news", "listicle", "overview",
    "guide", "what is", "explained", "academic opportunities", "ai discussions",
)


def corpus(item, source_text: str = "") -> str:
    meta = getattr(item, "metadata", {}) or {}
    parts = [getattr(item, "title", ""), getattr(item, "description", ""), source_text,
             meta.get("summary", ""), meta.get("search_snippet", "")]
    return " ".join(str(x or "") for x in parts).lower()


def _has_any(text: str, patterns) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


def classify_opportunity(item, requested_type: str, source_text: str = "") -> tuple[bool, str]:
    """Return (accepted, reason) using hard type-specific evidence."""
    if requested_type in (None, "", "All"):
        return True, "No hard type requested."
    if requested_type == "Master's":
        requested_type = "Study / Degree"
    text = corpus(item, source_text)
    positive = _has_any(text, POSITIVE.get(requested_type, ()))
    # What a page IS about is decided at its top (title + opening text). Words like "news",
    # "internship" or "blog" deep inside a genuine page (side links, related items) must not
    # disqualify it, so competing-type evidence is only searched in the head.
    head = " ".join([
        str(getattr(item, "title", "") or ""), str(getattr(item, "organization", "") or ""),
        (source_text or str(getattr(item, "description", "") or ""))[:1500],
    ]).lower()
    negative = _has_any(head, NEGATIVE.get(requested_type, ()))

    # Scholarship is intentionally strict: a Master's page is not a scholarship
    # merely because it mentions funding. Funding must be tied to a scholarship-like mechanism.
    if requested_type == "Scholarship":
        funding_signal = _has_any(text, POSITIVE["Scholarship"])
        if negative:
            return False, "Contains a competing opportunity type or non-actionable content."
        if not funding_signal:
            return False, "No scholarship/fellowship/grant/financial-aid mechanism found."
        if not _has_any(text, ACTION) and not _has_any(text, (r"\baward(?:ed|available)\b", r"\beligib(?:le|ility)\b")):
            return False, "Funding is mentioned without an actionable scholarship mechanism."
        return True, "Scholarship/funding mechanism and actionable evidence found."

    if requested_type == "Internship":
        if _has_any(head, NEGATIVE["Internship"]):
            # Negative scholarship-database phrase alone should not block an actual internship;
            # only block it when it is the dominant page type.
            if not positive:
                return False, "Not an internship opportunity."
        if not positive:
            return False, "No internship/placement/trainee evidence found."
        return True, "Internship evidence found."

    if requested_type == "Job":
        if _has_any(head, NEGATIVE["Job"]):
            return False, "Contains a non-job opportunity type."
        if not positive:
            return False, "No employment/vacancy/careers evidence found."
        return True, "Employment/vacancy evidence found."

    if requested_type == "Study / Degree":
        if _has_any(head, NEGATIVE["Study / Degree"]):
            return False, "Contains internship/employment evidence."
        if not positive:
            return False, "No degree/admissions evidence found."
        return True, "Degree/admissions evidence found."

    if requested_type == "Research":
        if _has_any(text, NEGATIVE["Research"]):
            return False, "Contains a competing opportunity type."
        if not positive:
            return False, "No research-position/doctoral/postdoc evidence found."
        return True, "Research-position evidence found."

    return True, "Type not constrained."


def page_is_non_actionable(item, source_text: str = "") -> bool:
    text = corpus(item, source_text)
    title = str(getattr(item, "title", "") or "").lower()
    if any(x in title for x in LEAD):
        return True
    # Keep an actual opportunity page even if it contains a generic word like "guide".
    if any(x in text[:5000] for x in LEAD) and not _has_any(text, ACTION):
        return True
    return False



# ---------------------------------------------------------------------------- aggregate listings
_AGG_TITLE = [
    r"^\s*\d[\d,.]*[kK+]*\s+(?:[\w\-/&' ]{0,40}?\s)?(?:jobs?|vacancies|positions|openings|internships?|careers?)\b",
    r"\b(?:job search|search jobs|find (?:a )?jobs?|browse jobs|job board|job listings?|job openings|current openings|open positions|all jobs|latest jobs|job alerts?)\b",
    r"\bjobs? (?:and|&) careers\b|\bcareers? (?:page|portal|site|opportunities)\b|\bwork with us\b|\bjoin our team\b|\bvacancies\b$",
]
_AGG_TITLE_CASE = re.compile(r"\b(?:[Jj]obs|[Vv]acancies|[Ii]nternships|[Oo]penings|[Pp]ositions)\s+(?:in|near)\s+[A-Z]")
_AGG_PATH = re.compile(r"(?:^|/)(?:jobs?|careers?|vacancies|internships?|openings|search|find-jobs?|jobs-in-[\w-]+|jobs/search)/?$", re.I)


def is_aggregate_listing(item, requested_type: str) -> bool:
    """True for pages that are a list/search of many jobs rather than one posting (e.g. '100 jobs available')."""
    if requested_type not in {"Job", "Internship", "Research"}:
        return False
    title = re.sub(r"\s+", " ", str(getattr(item, "title", "") or "")).strip()
    if any(re.search(p, title, re.I) for p in _AGG_TITLE) or _AGG_TITLE_CASE.search(title):
        return True
    from urllib.parse import urlparse
    url = str(getattr(item, "application_url", "") or getattr(item, "source_url", "") or "")
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if _AGG_PATH.search(parsed.path or "") and not parsed.query.lower().startswith(("id=", "job=")):
        return True
    return "jobs-in-" in (parsed.path or "").lower() or "/jobs/search" in (parsed.path or "").lower()
