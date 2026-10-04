"""Hard relevance gates that run on the fetched source page.

A search engine only says "this URL matched some words". These gates decide whether the
page really is ONE opportunity of the requested type, level and country. They are
deterministic, so the app stays correct with no AI provider configured.
"""
from __future__ import annotations

import re

from intelligence.geo import country_matches

# ---------------------------------------------------------------- scholarship-family words
SCHOLAR_STRONG = re.compile(
    r"\b(scholarships?|scholars?|fellowships?|bursar(?:y|ies)|studentships?|stipends?|stipendium|beasiswa|"
    r"tuition[- ]waivers?|financial aid)\b", re.I)
SCHOLAR_ANY = re.compile(
    r"\b(scholarships?|scholars?|fellowships?|bursar(?:y|ies)|studentships?|stipends?|stipendium|grants?|awards?|"
    r"funding|funded|tuition[- ]waivers?|financial aid|erasmus mundus|chevening|fulbright|daad)\b", re.I)

# ---------------------------------------------------------------- job posting detection
JOB_ROLE_TITLE = re.compile(
    r"\b(manager|engineer|developer|executive|specialist|officer|analyst|director|leader|assistant|designer|trainer|"
    r"coordinator|consultant|architect|technician|recruiter|administrator|accountant|representative|supervisor|"
    r"programmer|scientist|head of|chief|cto|ceo|cfo|vp|intern|trainee|praktikum|werkstudent|working student|"
    r"associate|lecturer|professor|teacher|instructor)\b", re.I)
GENDER_TAG = re.compile(r"\((?:[mfwdx]\s*/\s*){1,3}[mfwdx]\)|\b[mfwd]/[mfwd]/[mfwdx]\b", re.I)
JOB_BODY = [re.compile(p, re.I) for p in (
    r"\bresponsibilit(?:y|ies)\b", r"\bwe are looking for\b", r"\byour profile\b", r"\bwhat we offer\b",
    r"\bfull[- ]time\b", r"\bsalary\b", r"\bjob description\b", r"\b\d+\+? years? of (?:professional |relevant )?experience\b",
    r"\bapply for this (?:job|position|role)\b", r"\bjoin our team\b", r"\bwho you are\b", r"\bpermanent contract\b",
    r"\bequal opportunity employer\b", r"\bkey duties\b", r"\bwhat you.ll do\b",
)]


def job_signals(text: str) -> int:
    return sum(1 for rx in JOB_BODY if rx.search(text or ""))


def looks_like_job_posting(title: str, text: str) -> bool:
    title = title or ""
    if GENDER_TAG.search(title):
        return True
    if JOB_ROLE_TITLE.search(title) and not SCHOLAR_STRONG.search(title):
        return True
    return job_signals((text or "")[:5000]) >= 3


# ---------------------------------------------------------------- navigation / sub-pages / indexes
NAV_TITLE = re.compile(
    r"^\s*(selecting|how to|eligible|eligibility|faq|frequently asked|contact|about(?: us)?|overview|resources|"
    r"faculty|guest speakers|speakers|staff|news|events?|people|our team|history|policies|privacy|terms|"
    r"login|log in|sign in|home|welcome|search|sitemap|apply(?: now| online)?$|application (?:process|tips|guide))\b", re.I)
INDEX_TITLE = re.compile(
    r"\b(scholarships?|funding|grants?|fellowships?|financial aid|opportunities)\s+"
    r"(database|directory|finder|search|listing|listings|portal|catalogue|catalog|index|search engine)\b|"
    r"\b(search|browse|find)\s+(?:a\s+|for\s+)?(scholarships?|funding|grants?)\b|"
    r"^\s*(?:all\s+)?(scholarships?|funding|grants?)\s*$|\bscholarships? (?:and|&) (?:funding|grants?)\s*$|"
    r"\b(?:\d[\d,]*\+?)\s+(?:fully[- ]funded\s+)?scholarships?\b|\b(?:top|best)\s+\d*\s*scholarships?\b|"
    r"\blist of scholarships\b", re.I)


def is_navigational_title(title: str) -> bool:
    return bool(NAV_TITLE.search(title or ""))


def is_scholarship_index(title: str) -> bool:
    return bool(INDEX_TITLE.search(title or ""))


# ---------------------------------------------------------------- levels
LEVEL_RX = {
    "Bachelor's": re.compile(r"\b(bachelor'?s?|undergraduate|undergrad|bsc|b\.sc|first[- ]degree)\b", re.I),
    "Master's": re.compile(r"\b(master'?s?|msc|m\.sc|postgraduate|post-graduate|graduate (?:students?|programmes?|programs?|degrees?|studies)|mba|llm)\b", re.I),
    "PhD": re.compile(r"\b(ph\.?\s?d\.?|doctoral|doctorate|dphil|doctoral candidates?)\b", re.I),
    "Postdoc": re.compile(r"\b(post-?docs?|postdoctoral|post-doctoral)\b", re.I),
}
RA_RX = re.compile(r"\b(research assistant|research associate|research officer|research intern)\b", re.I)


def detect_levels(text: str) -> list[str]:
    return [name for name, rx in LEVEL_RX.items() if rx.search(text or "")]


def level_label(item_title: str, page_text: str) -> str:
    levels = detect_levels(f"{item_title} {(page_text or '')[:1500]}")
    return " · ".join(levels)


def level_ok(title: str, page_text: str, requested: str | None) -> tuple[bool, str]:
    """Reject a page that is clearly about a different study/research level."""
    requested = (requested or "Any").strip()
    if requested in {"", "Any"}:
        return True, "No level requested."
    title_levels = detect_levels(title)
    zone = f"{title} {(page_text or '')[:1500]}"
    if requested == "Research Assistant":
        return (True, "ok") if RA_RX.search(zone) or not detect_levels(zone) else (False, "Different research level.")
    if "Postdoc" in title_levels and requested != "Postdoc":
        return False, "Postdoctoral opportunity, not the requested level."
    levels = detect_levels(zone)
    if not levels:
        return True, "Level not stated on the page."
    if requested in levels:
        return True, f"Level matches ({requested})."
    return False, f"Page is for {', '.join(levels)}, not {requested}."


# ---------------------------------------------------------------- combined gate
def identity_zone(item, page_text: str) -> str:
    """Title + organization + the first lines of the page: what the page IS about."""
    return " ".join([str(getattr(item, "title", "") or ""), str(getattr(item, "organization", "") or ""),
                     (page_text or "")[:700]])


def single_scholarship_ok(item, page_text: str) -> tuple[bool, str]:
    title = str(getattr(item, "title", "") or "")
    meta = getattr(item, "metadata", {}) or {}
    curated = bool(meta.get("library_seed")) and meta.get("library_source_kind") != "catalogue"
    if meta.get("library_source_kind") == "catalogue":
        return False, "Catalogue/database page: its individual scholarships are listed instead."
    if is_scholarship_index(title):
        return False, "Scholarship database, directory or list, not one scholarship."
    if looks_like_job_posting(title, page_text):
        return False, "Job posting, not a scholarship."
    if is_navigational_title(title) and not SCHOLAR_STRONG.search(title):
        return False, "Navigation or information sub-page, not a scholarship."
    if curated:
        return True, "Curated scholarship programme."
    if SCHOLAR_ANY.search(title) or SCHOLAR_ANY.search(identity_zone(item, page_text)):
        return True, "Scholarship wording in the title or opening text."
    return False, "The page title/opening text does not describe a scholarship."


def study_programme_ok(item, page_text: str) -> tuple[bool, str]:
    title = str(getattr(item, "title", "") or "")
    if looks_like_job_posting(title, page_text):
        return False, "Job posting, not a study programme."
    if is_navigational_title(title) and not detect_levels(title):
        return False, "Navigation or information sub-page."
    return True, "ok"


def research_position_ok(item, page_text: str) -> tuple[bool, str]:
    title = str(getattr(item, "title", "") or "")
    if is_navigational_title(title):
        return False, "Navigation or information sub-page."
    if re.search(r"\b(scholarship database|internship)\b", title, re.I):
        return False, "Competing opportunity type."
    return True, "ok"


def relevance_gate(item, requested_type: str, page_text: str, countries=None, study_level="Any",
                   research_level="Any") -> tuple[bool, str]:
    """Single entry point used by the planner after the real page has been fetched."""
    rt = "Study / Degree" if requested_type == "Master's" else requested_type
    if rt == "Scholarship":
        ok, why = single_scholarship_ok(item, page_text)
    elif rt == "Study / Degree":
        ok, why = study_programme_ok(item, page_text)
    elif rt == "Research":
        ok, why = research_position_ok(item, page_text)
    else:
        ok, why = True, "ok"
    if not ok:
        return False, why
    title = str(getattr(item, "title", "") or "")
    if rt in {"Scholarship", "Study / Degree"}:
        ok, why = level_ok(title, page_text, study_level)
        if not ok:
            return False, why
    elif rt == "Research":
        ok, why = level_ok(title, page_text, research_level)
        if not ok:
            return False, why
    structured = bool((getattr(item, "metadata", {}) or {}).get("structured_listing"))
    if rt in {"Scholarship", "Study / Degree", "Research"} and not structured:
        if not country_matches(item, page_text, list(countries or [])):
            return False, "The page does not relate to any selected country."
    return True, "Passed relevance checks."
