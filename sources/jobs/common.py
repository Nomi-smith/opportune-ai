"""Shared helpers for keyless job-board sources (individual postings only)."""
from __future__ import annotations

import re
import time

import httpx

from sources.jobs.arbeitnow import _clean_html, _score_job, _tokens  # noqa: F401  (re-exported)

# Words the planner adds to every query lane; they describe the search, not the role.
_NOISE_WORDS = {
    "current", "open", "hiring", "vacancy", "vacancies", "jobs", "job", "careers", "career", "apply",
    "employer", "official", "portal", "international", "students", "student", "placement", "applications",
    "application", "paid", "company", "intern", "internship", "internships", "or", "and", "site", "the",
    "for", "in", "of", "to", "a", "2025", "2026", "2027", "2028", "fully", "funded",
}

_CACHE: dict[str, tuple[float, object]] = {}


def clean_role_query(query: str, country: str | None = None) -> str:
    """Reduce a decorated search-lane string to the role/skill words only."""
    text = re.sub(r"\([^)]*site:[^)]*\)", " ", query or "", flags=re.I)
    text = re.sub(r"\bsite:\S+", " ", text, flags=re.I)
    drop = set(_tokens(country or ""))
    words = [w for w in _tokens(text) if w not in _NOISE_WORDS and w not in drop]
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return " ".join(out[:8])


async def cached_json(url: str, params: dict | None = None, ttl: int = 3600, timeout: float = 20.0):
    """One request per URL per `ttl` seconds per process (these APIs ask clients not to poll)."""
    key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OpportuneAI/1.0; personal job search)"}
    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    _CACHE[key] = (time.time(), data)
    return data


_GLOBAL_WORDS = ("worldwide", "anywhere", "global", "remote", "international")


def location_ok(location: str, country: str | None) -> bool:
    """Country filter for remote boards: keep postings open to the requested country or to everyone."""
    if not country:
        return True
    loc = (location or "").lower()
    if not loc.strip():
        return True
    tokens = _tokens(country)
    if tokens and all(t in loc for t in tokens):
        return True
    return any(w in loc for w in ("worldwide", "anywhere", "global"))


def work_mode(*texts: str) -> str:
    blob = " ".join(texts).lower()
    if "hybrid" in blob:
        return "Hybrid"
    if "remote" in blob or "work from home" in blob or "anywhere" in blob:
        return "Remote"
    return "On-site"


def is_intern_title(title: str, tags=None) -> bool:
    blob = (title + " " + " ".join(tags or [])).lower()
    return any(x in blob for x in ("intern", "internship", "trainee", "working student", "apprentice"))


def build_job(source: str, kind: str, uid: str, title: str, company: str, location: str, url: str,
              description: str, posted, job_type: str = "", salary: str = "", tags=None, remote=None, country=None):
    from models.opportunity import Opportunity
    mode = "Remote" if remote else work_mode(location, title)
    return Opportunity(
        id=f"{source}:{uid}", title=title, organization=company, opportunity_type=kind,
        country=country or None, city=location or None, description=description, application_url=url,
        source_url=url, source_name=source, verification_status="UNVERIFIED",
        compensation=salary or None, work_mode=mode,
        metadata={"structured_listing": True, "discovery_type": "DIRECT_PAGE", "posted_date": str(posted or ""),
                  "work_mode": mode, "salary": salary, "job_type": job_type, "tags": list(tags or []), "location_text": location,
                  "source_tier": "database"},
    )
