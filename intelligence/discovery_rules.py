"""Hard relevance rules for opportunity discovery.

The discovery engine should never silently substitute a different degree level,
destination country, or page type for the user's request.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

LEVEL_MARKERS = {
    "Bachelor's": ("bachelor", "bachelors", "bachelor's", "bachelor’s", "bsc", "b.sc", "undergraduate"),
    "Master's": ("master", "masters", "master's", "master’s", "msc", "m.sc", "m.a.", "ma ", "meng", "m.eng"),
    "PhD": ("phd", "ph.d", "doctoral", "doctorate", "dphil"),
}

TYPE_MARKERS = {
    "Study / Degree": ("admission", "admissions", "degree programme", "degree program", "study programme", "study program", "master", "bachelor", "undergraduate", "postgraduate"),
    "Scholarship": ("scholarship", "fellowship", "grant", "funding", "financial aid", "stipend", "tuition waiver", "award"),
    "Research": ("research", "research position", "research assistant", "research group", "laboratory", "lab", "professor", "postdoc", "phd"),
    "Job": ("job", "career", "vacancy", "position", "hiring", "employment"),
    "Internship": ("internship", "intern", "trainee", "placement", "working student"),
}

COUNTRY_ALIASES = {
    "Germany": ("germany", "german", "deutschland", "deutsch"),
    "Netherlands": ("netherlands", "dutch", "holland"),
    "Sweden": ("sweden", "swedish"),
    "Finland": ("finland", "finnish"),
    "Denmark": ("denmark", "danish"),
    "Norway": ("norway", "norwegian"),
    "France": ("france", "french"),
    "Italy": ("italy", "italian"),
    "Spain": ("spain", "spanish"),
    "Portugal": ("portugal", "portuguese"),
    "Austria": ("austria", "austrian"),
    "Switzerland": ("switzerland", "swiss"),
    "Belgium": ("belgium", "belgian"),
    "United Kingdom": ("united kingdom", "uk", "britain", "british", "england", "scotland", "wales"),
    "Ireland": ("ireland", "irish"),
    "Poland": ("poland", "polish"),
    "Czech Republic": ("czech republic", "czechia", "czech"),
    "Hungary": ("hungary", "hungarian"),
    "Türkiye": ("turkey", "türkiye", "turkish"),
    "Romania": ("romania", "romanian"),
    "Estonia": ("estonia", "estonian"),
    "Latvia": ("latvia", "latvian"),
    "Lithuania": ("lithuania", "lithuanian"),
    "Greece": ("greece", "greek"),
    "United States": ("united states", "usa", "u.s.", "american", "us"),
    "Canada": ("canada", "canadian"),
    "Australia": ("australia", "australian"),
    "New Zealand": ("new zealand", "new zealand"),
    "Japan": ("japan", "japanese"),
    "South Korea": ("south korea", "korea", "republic of korea", "korean"),
    "China": ("china", "chinese", "prc", "people's republic of china", "people’s republic of china"),
    "Singapore": ("singapore", "singaporean"),
    "Malaysia": ("malaysia", "malaysian"),
    "United Arab Emirates": ("united arab emirates", "uae", "emirates"),
    "Saudi Arabia": ("saudi arabia", "saudi"),
    "Qatar": ("qatar", "qatari"),
    "Pakistan": ("pakistan", "pakistani"),
    "India": ("india", "indian"),
    "South Africa": ("south africa", "south african"),
    "Brazil": ("brazil", "brazilian"),
}


def clean_text(*parts: object) -> str:
    return " ".join(str(p or "") for p in parts).lower()


def level_markers(level: str) -> tuple[str, ...]:
    return LEVEL_MARKERS.get(level, ())


def detect_levels(text: str) -> set[str]:
    low = clean_text(text)
    found = set()
    for level, markers in LEVEL_MARKERS.items():
        if any(re.search(r"(?<![a-z])" + re.escape(marker.strip()) + r"(?![a-z])", low) for marker in markers):
            found.add(level)
    return found


def title_is_wrong_level(title: str, requested_level: str) -> bool:
    low = clean_text(title)
    opposing = {
        "Bachelor's": ("master", "msc", "phd", "doctoral", "doctorate"),
        "Master's": ("phd", "doctoral", "doctorate", "dphil"),
        "PhD": ("bachelor", "undergraduate", "master", "msc"),
    }.get(requested_level, ())
    wanted = level_markers(requested_level)
    if wanted and any(m.strip() in low for m in wanted):
        return False
    return any(m in low for m in opposing)


def level_matches(text: str, requested_level: str | None) -> bool:
    if not requested_level or requested_level == "Any":
        return True
    low = clean_text(text)
    wanted = level_markers(requested_level)
    if not any(m.strip() in low for m in wanted):
        return False
    # A page whose title is explicitly a different level is not a match.
    title = low[:500]
    return not title_is_wrong_level(title, requested_level)


def country_matches(text: str, url: str, country: str | None, preferred_domains: list[str] | None = None) -> bool:
    if not country or country in {"Any country", "Other / Custom"}:
        return True
    low = clean_text(text)
    aliases = COUNTRY_ALIASES.get(country, (country.lower(),))
    if any(re.search(r"(?<![a-z])" + re.escape(a) + r"(?![a-z])", low) for a in aliases):
        return True
    host = urlparse(url or "").netloc.lower().replace("www.", "")
    for domain in preferred_domains or []:
        d = domain.lower().replace("www.", "")
        if host == d or host.endswith("." + d):
            return True
    return False


def type_matches(text: str, opportunity_type: str) -> bool:
    if opportunity_type in (None, "All"):
        return True
    low = clean_text(text)
    return any(marker in low for marker in TYPE_MARKERS.get(opportunity_type, ()))


def is_discussion_or_article(text: str) -> bool:
    low = clean_text(text)
    bad = (
        "discussion", "forum", "community", "reddit", "quora", "blog post",
        "news article", "how to", "what is", "explained", "overview", "guide", "listicle", "top 10", "top 20", "best scholarships", "best universities",
        "academic opportunities", "ai discussions",
    )
    return any(x in low for x in bad)
