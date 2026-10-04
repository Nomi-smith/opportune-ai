"""Country matching for discovery results (aliases, demonyms and domain suffixes)."""
from __future__ import annotations

import re
from urllib.parse import urlparse

# canonical name (as in COUNTRY_OPTIONS) -> extra words that mean the same place
ALIASES: dict[str, tuple[str, ...]] = {
    "United Kingdom": ("united kingdom", "uk", "u.k.", "britain", "british", "england", "scotland", "wales", "northern ireland"),
    "United States": ("united states", "usa", "u.s.", "u.s.a", "america", "american"),
    "South Korea": ("south korea", "korea", "korean", "republic of korea"),
    "China": ("china", "chinese", "prc", "p.r. china"),
    "Türkiye": ("türkiye", "turkiye", "turkey", "turkish"),
    "Czech Republic": ("czech republic", "czechia", "czech"),
    "United Arab Emirates": ("united arab emirates", "uae", "emirates", "dubai", "abu dhabi"),
    "Netherlands": ("netherlands", "the netherlands", "dutch", "holland"),
    "Germany": ("germany", "german", "deutschland"),
    "France": ("france", "french"),
    "Japan": ("japan", "japanese"),
    "Sweden": ("sweden", "swedish"),
    "Finland": ("finland", "finnish"),
    "Denmark": ("denmark", "danish"),
    "Norway": ("norway", "norwegian"),
    "Italy": ("italy", "italian"),
    "Spain": ("spain", "spanish"),
    "Switzerland": ("switzerland", "swiss"),
    "Australia": ("australia", "australian"),
    "Canada": ("canada", "canadian"),
    "New Zealand": ("new zealand",),
    "Singapore": ("singapore", "singaporean"),
    "Malaysia": ("malaysia", "malaysian"),
    "Saudi Arabia": ("saudi arabia", "saudi", "ksa"),
    "Pakistan": ("pakistan", "pakistani"),
    "India": ("india", "indian"),
    "South Africa": ("south africa", "south african"),
    "Brazil": ("brazil", "brazilian"),
    "Ireland": ("ireland", "irish"),
    "Austria": ("austria", "austrian"),
    "Belgium": ("belgium", "belgian"),
    "Poland": ("poland", "polish"),
    "Hungary": ("hungary", "hungarian"),
    "Portugal": ("portugal", "portuguese"),
    "Greece": ("greece", "greek"),
    "Romania": ("romania", "romanian"),
    "Estonia": ("estonia", "estonian"),
    "Latvia": ("latvia", "latvian"),
    "Lithuania": ("lithuania", "lithuanian"),
    "Qatar": ("qatar", "qatari"),
}

TLDS: dict[str, tuple[str, ...]] = {
    "United Kingdom": (".uk",), "United States": (".edu", ".us"), "South Korea": (".kr",), "China": (".cn",),
    "Türkiye": (".tr",), "Czech Republic": (".cz",), "United Arab Emirates": (".ae",), "Netherlands": (".nl",),
    "Germany": (".de",), "France": (".fr",), "Japan": (".jp",), "Sweden": (".se",), "Finland": (".fi",),
    "Denmark": (".dk",), "Norway": (".no",), "Italy": (".it",), "Spain": (".es",), "Switzerland": (".ch",),
    "Australia": (".au",), "Canada": (".ca",), "New Zealand": (".nz",), "Singapore": (".sg",), "Malaysia": (".my",),
    "Saudi Arabia": (".sa",), "Pakistan": (".pk",), "India": (".in",), "South Africa": (".za",), "Brazil": (".br",),
    "Ireland": (".ie",), "Austria": (".at",), "Belgium": (".be",), "Poland": (".pl",), "Hungary": (".hu",),
    "Portugal": (".pt",), "Greece": (".gr",), "Romania": (".ro",), "Estonia": (".ee",), "Latvia": (".lv",),
    "Lithuania": (".lt",), "Qatar": (".qa",),
}


def _canon(country: str) -> str:
    low = (country or "").strip().casefold()
    for name in ALIASES:
        if name.casefold() == low:
            return name
    return (country or "").strip()


def terms_for(country: str) -> tuple[str, ...]:
    name = _canon(country)
    return ALIASES.get(name) or ((name.casefold(),) if name else ())


def _word_in(term: str, text: str) -> bool:
    return bool(re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text))


def mentions_country(text: str, country: str) -> bool:
    low = (text or "").casefold()
    return any(_word_in(t, low) for t in terms_for(country))


def host_matches_country(url: str, country: str) -> bool:
    host = urlparse(url or "").netloc.lower().split(":")[0]
    name = _canon(country)
    suffixes = TLDS.get(name, ())
    # .edu is the US convention but is also used elsewhere only rarely; accept it for the US only.
    return any(host.endswith(s) for s in suffixes)


def country_matches(item, text: str, countries: list[str]) -> bool:
    """True if the page is plausibly about any of the selected countries."""
    wanted = [c for c in countries if c and c.strip()]
    if not wanted:
        return True
    url = str(getattr(item, "application_url", "") or getattr(item, "source_url", "") or "")
    own = " ".join(str(getattr(item, f, "") or "") for f in ("country", "city", "title", "organization"))
    zone = (text or "")[:8000]
    for c in wanted:
        if mentions_country(own, c) or host_matches_country(url, c) or mentions_country(zone, c):
            return True
    return False
