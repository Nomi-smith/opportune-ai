import asyncio
import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from intelligence.requirements import extract_required_skills, extract_requirements
from models.opportunity import Opportunity
from sources.base import BaseSource

SEARCH_ENGINE_HOSTS = {
    "duckduckgo.com", "www.duckduckgo.com", "google.com", "www.google.com",
    "bing.com", "www.bing.com", "search.yahoo.com",
}
LISTING_MARKERS = (
    "/jobs/search", "/job-search", "/search/jobs", "/jobs/collections",
    "/jobs/browse", "/opportunities/search", "/internships/search",
    "/scholarships/search", "/search/results",
)


def unwrap_search_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if parsed.netloc.lower() not in SEARCH_ENGINE_HOSTS:
        return href
    qs = parse_qs(parsed.query)
    for key in ("uddg", "url", "q"):
        if qs.get(key):
            return unquote(qs[key][0])
    return ""


def unwrap_bing_url(href: str) -> str:
    """Bing wraps result links as bing.com/ck/a?...&u=a1<urlsafe-base64(real url)>."""
    import base64
    parsed = urlparse(href or "")
    if "bing.com" not in parsed.netloc.lower():
        return href or ""
    token = (parse_qs(parsed.query).get("u") or [""])[0]
    if token.startswith("a1"):
        token = token[2:]
        try:
            return base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)).decode("utf-8")
        except Exception:
            return ""
    return ""


def is_listing_page(url: str) -> bool:
    parsed = urlparse(url)
    full = ((parsed.path or "") + "?" + (parsed.query or "")).lower()
    if any(marker in full for marker in LISTING_MARKERS):
        return True
    return False


def _type_query(query: str, opportunity_type: str | None) -> str:
    q = (query or "").strip()
    templates = {
        "Job": f"({q}) job careers hiring vacancy position",
        "Internship": f"({q}) internship intern trainee placement",
        "Master's": f"({q}) (master OR masters OR MSc OR postgraduate) (admission OR admissions OR program OR programme) university",
        "Study / Degree": f"({q}) (bachelor OR undergraduate OR master OR masters OR MSc OR PhD OR doctoral) (admission OR admissions OR program OR programme) university",
        "Scholarship": f"({q}) (scholarship OR fellowship OR funding OR grant OR stipend) international students",
        "Research": f"({q}) (research OR professor OR laboratory OR lab OR research assistant OR PhD OR postdoc) university",
        "All": f"({q}) (job OR internship OR scholarship OR fellowship OR admissions OR research OR opportunity)",
    }
    return templates.get(opportunity_type or "All", templates["All"])


def _page_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header", "form"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)[:24000]


def _organization(soup: BeautifulSoup, url: str) -> str:
    for selector, attr in [
        (("meta", {"property": "og:site_name"}), "content"),
        (("meta", {"name": "application-name"}), "content"),
    ]:
        tag = soup.find(*selector)
        if tag and tag.get(attr):
            return tag.get(attr).strip()
    host = urlparse(url).netloc.lower().replace("www.", "")
    return host


def _title(soup: BeautifulSoup, fallback: str) -> str:
    tag = soup.find("meta", attrs={"property": "og:title"}) or soup.find("title")
    value = tag.get("content") if tag and tag.name == "meta" else tag.get_text(" ", strip=True) if tag else ""
    return (value or fallback).strip()[:300]


def _matches_type(text: str, opportunity_type: str | None) -> bool:
    if not opportunity_type or opportunity_type == "All":
        return True
    t = text.lower()
    markers = {
        "Job": ("job", "career", "vacancy", "position", "hiring"),
        "Internship": ("internship", "intern", "trainee", "placement"),
        "Master's": ("master", "msc", "postgraduate", "admission", "degree programme", "degree program"),
        "Study / Degree": ("bachelor", "undergraduate", "master", "msc", "phd", "doctoral", "admission", "degree programme", "degree program"),
        "Scholarship": ("scholarship", "fellowship", "funding", "grant", "stipend", "financial aid"),
        "Research": ("research", "professor", "laboratory", "lab", "research assistant", "phd", "postdoc"),
    }
    return any(marker in t for marker in markers.get(opportunity_type, ()))


class PublicWebSource(BaseSource):
    name = "Global Public Web"

    async def _fetch_page(self, client, url: str):
        try:
            response = await client.get(url)
            if response.status_code >= 400 or "text/html" not in response.headers.get("content-type", ""):
                return None, ""
            soup = BeautifulSoup(response.text, "html.parser")
            text = _page_text(soup)
            return soup, text
        except Exception:
            return None, ""

    async def search(self, query: str, opportunity_type: str | None = None, country: str | None = None):
        search_query = _type_query(query or "opportunities", opportunity_type)
        if country:
            search_query += f' "{country}"'
        search_url = "https://html.duckduckgo.com/html/?q=" + quote_plus(search_query)

        try:
            async with httpx.AsyncClient(
                timeout=25,
                headers={"User-Agent": "OpportuneAI/1.0 (global opportunity discovery)"},
                follow_redirects=True,
            ) as client:
                response = await client.get(search_url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                candidates, seen = [], set()
                for result in soup.select(".result")[:30]:
                    link = result.select_one(".result__a")
                    if not link:
                        continue
                    href = unwrap_search_url(link.get("href", ""))
                    parsed = urlparse(href)
                    if not href or not parsed.netloc or parsed.netloc.lower() in SEARCH_ENGINE_HOSTS or is_listing_page(href):
                        continue
                    if href in seen:
                        continue
                    seen.add(href)
                    candidates.append((link.get_text(" ", strip=True), href))

                if not candidates:
                    # Keyless fallback when DuckDuckGo returns nothing (rate limit / challenge page).
                    try:
                        bing = await client.get("https://www.bing.com/search?q=" + quote_plus(search_query) + "&count=30")
                        bsoup = BeautifulSoup(bing.text, "html.parser")
                        for link in bsoup.select("li.b_algo h2 a")[:25]:
                            href = unwrap_bing_url(link.get("href", ""))
                            parsed = urlparse(href)
                            if (not href.startswith("http") or not parsed.netloc or parsed.netloc.lower() in SEARCH_ENGINE_HOSTS
                                    or is_listing_page(href) or href in seen):
                                continue
                            seen.add(href)
                            candidates.append((link.get_text(" ", strip=True), href))
                    except Exception:
                        pass

                async def process(search_title, href):
                    page, text = await self._fetch_page(client, href)
                    if not page or not text or is_listing_page(href) or not _matches_type(text, opportunity_type):
                        return None
                    title = _title(page, search_title)
                    organization = _organization(page, href)
                    skills = extract_required_skills(text)
                    requirements = extract_requirements(text)
                    lower = (title + " " + text[:12000]).lower()
                    # Prevent ordinary articles/search pages from becoming fake opportunities.
                    action_signal = any(x in lower for x in (
                        "apply", "application", "eligibility", "requirements", "admission",
                        "deadline", "vacancy", "position", "scholarship", "fellowship",
                        "internship", "hiring", "research assistant", "apply now", "how to apply",
                    ))
                    if not action_signal:
                        return None
                    return Opportunity(
                        title=title,
                        organization=organization,
                        opportunity_type=(opportunity_type or "UNKNOWN").upper(),
                        description=text[:5000],
                        requirements=requirements,
                        application_url=href,
                        source_url=href,
                        source_name=self.name,
                        verification_status="UNVERIFIED",
                        metadata={
                            "discovery_type": "DIRECT_PAGE",
                            "source_kind": "PUBLIC_WEB",
                            "destination_url": href,
                            "required_skills": skills,
                            "search_query": search_query,
                        },
                    )

                results = await asyncio.gather(*(process(title, href) for title, href in candidates))
                return [item for item in results if item]
        except Exception:
            return []
