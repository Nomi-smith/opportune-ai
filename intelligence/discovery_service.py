"""Single entry point for running discovery from the UI (Discover pages and the AI Agent).

It wires the existing SourceManager + DiscoveryPlanner together and applies the same
source-fact post-processing everywhere, so every surface uses one discovery engine.
"""
from __future__ import annotations

import asyncio
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from intelligence.discovery_planner import DiscoveryPlanner
from intelligence.opportunity_intelligence import extract_opportunity_details
from intelligence.source_facts import apply_source_facts
from sources.gemini_google_search import GeminiGoogleSearchSource
from sources.jobs.arbeitnow import ArbeitnowSource
from sources.jobs.jobicy import JobicySource
from sources.jobs.remotive import RemotiveSource
from sources.manager import SourceManager
from sources.openrouter_search import OpenRouterWebSearchSource
from sources.research.openalex import OpenAlexSource
from sources.scholarship_library_source import ScholarshipLibrarySource
from sources.serper import SerperGoogleSource
from sources.web import PublicWebSource

# Search-engine / grounding redirect hosts are discovery plumbing, never a destination.
_REDIRECT_HOSTS = ("vertexaisearch.cloud.google.com",)


def canonical_url(url: str) -> str:
    """Normalise a URL so the same page found through different searches compares equal."""
    try:
        p = urlparse((url or "").strip())
    except Exception:
        return (url or "").strip()
    query = urlencode([(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(("utm_", "fbclid", "gclid"))])
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), p.netloc.lower().replace("www.", "", 1), path, "", query, ""))


def merge_same_page(items):
    """One result per real page. If several country searches surfaced it, the page is not specific
    to any one of them, so the searched countries are kept in metadata and Country is left to the source."""
    merged, order = {}, []
    for item in items:
        key = canonical_url(getattr(item, "application_url", "") or getattr(item, "source_url", "")) or id(item)
        if key not in merged:
            merged[key] = item
            order.append(key)
            meta = dict(getattr(item, "metadata", {}) or {})
            meta["searched_countries"] = [c for c in [getattr(item, "country", None)] if c]
            item.metadata = meta
            continue
        keeper = merged[key]
        meta = dict(keeper.metadata or {})
        country = getattr(item, "country", None)
        seen = meta.setdefault("searched_countries", [])
        if country and country not in seen:
            seen.append(country)
        if len(seen) > 1:
            keeper.country = None
        keeper.metadata = meta
    return [merged[k] for k in order]


async def fix_truncated_titles(items, concurrency: int = 8):
    """Search engines often cut titles ('Master's in Data ...'). Replace those with the page's own title."""
    from sources.webfetch import fetch_page
    todo = [i for i in items if str(getattr(i, "title", "") or "").rstrip().endswith(("...", "\u2026"))]
    if not todo:
        return items
    gate = asyncio.Semaphore(concurrency)

    async def fix(item):
        url = getattr(item, "application_url", "") or getattr(item, "source_url", "")
        async with gate:
            page = await fetch_page(url, timeout=5, max_chars=200)
        title = (page or {}).get("title", "")
        if len(title) >= 12 and not title.endswith(("...", "\u2026")):
            item.title = title
    await asyncio.gather(*(fix(i) for i in todo), return_exceptions=True)
    return items


def is_expired(item) -> bool:
    """Last safety net: True if the item's final deadline is in the past or it says it is closed."""
    from datetime import date
    from intelligence.freshness import _dates, CLOSED_MARKERS
    dates = _dates(str(getattr(item, "deadline", "") or ""))
    if dates and max(dates) < date.today():
        return True
    head = " ".join([str(getattr(item, "title", "") or ""), str(getattr(item, "deadline", "") or "")]).casefold()
    return any(m in head for m in CLOSED_MARKERS)


def default_source_manager() -> SourceManager:
    return SourceManager([
        GeminiGoogleSearchSource(), OpenRouterWebSearchSource(), SerperGoogleSource(),
        ScholarshipLibrarySource(), ArbeitnowSource(), RemotiveSource(), JobicySource(), OpenAlexSource(), PublicWebSource(),
    ])


async def _resolve_one(item, client: httpx.AsyncClient, gate: asyncio.Semaphore):
    url = getattr(item, "application_url", "") or getattr(item, "source_url", "")
    host = urlparse(url or "").netloc.lower()
    if not any(host == h or host.endswith("." + h) for h in _REDIRECT_HOSTS):
        return
    async with gate:
        try:
            response = await client.get(url)
            final = str(response.url)
        except Exception:
            return
    if urlparse(final).netloc.lower() and not any(h in final for h in _REDIRECT_HOSTS):
        meta = dict(getattr(item, "metadata", {}) or {})
        meta["grounding_redirect_url"] = url
        item.metadata = meta
        item.application_url = final
        item.source_url = final


async def resolve_final_urls(items, concurrency: int = 8, timeout: float = 6.0):
    """Replace grounding-redirect URLs with the real destination page (bounded concurrency)."""
    if not any(
        any(h in (getattr(i, "application_url", "") or getattr(i, "source_url", "") or "") for h in _REDIRECT_HOSTS)
        for i in items
    ):
        return items
    gate = asyncio.Semaphore(concurrency)
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OpportuneAI/1.0; public research)"}
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        await asyncio.gather(*(_resolve_one(i, client, gate) for i in items), return_exceptions=True)
    return items


def search_opportunities(query, opportunity_type=None, roles=None, countries=None, fields=None,
                         profile=None, study_level="Any", research_level="Any"):
    """Run the full discovery pipeline. Returns (opportunities, source_diagnostics)."""
    async def run():
        manager = default_source_manager()
        planner = DiscoveryPlanner(manager)
        plan = planner.build_plan(opportunity_type or "Master's", roles or [], countries or [], fields or [],
                                  query, profile or {}, study_level, research_level)
        results = await planner.run(plan)
        results = await resolve_final_urls(results)
        results = merge_same_page(results)
        results = await fix_truncated_titles(results)
        final = []
        for item in results:
            # Structured job-board records already know their work mode, pay and location.
            structured = bool((item.metadata or {}).get("structured_listing"))
            item = extract_opportunity_details(item)
            item = apply_source_facts(item)
            if structured:
                meta = item.metadata or {}
                if str(item.work_mode or "").strip() in {"", "N/A", "None"} and meta.get("work_mode"):
                    item.work_mode = meta["work_mode"]
                if str(item.compensation or "").strip() in {"", "N/A", "None"} and meta.get("salary"):
                    item.compensation = meta["salary"]
            if is_expired(item):
                continue
            final.append(item)
        return final, manager.diagnostics
    return asyncio.run(run())
