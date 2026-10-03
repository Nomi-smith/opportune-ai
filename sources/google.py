import asyncio
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config.settings import GEMINI_API_KEY, GOOGLE_API_KEY, GOOGLE_CSE_ID, SERPER_API_KEY
from intelligence.requirements import extract_required_skills, extract_requirements
from models.opportunity import Opportunity
from sources.base import BaseSource


TYPE_TERMS = {
    "Job": 'job OR jobs OR careers OR vacancy',
    "Internship": 'internship OR intern OR trainee OR placement',
    "Master\'s": 'master OR masters OR MSc OR "master degree" OR admissions OR "graduate program"',
    "Scholarship": 'scholarship OR fellowship OR funding OR stipend OR "tuition waiver" OR "financial aid"',
    "Research": '"research position" OR "research assistant" OR professor OR laboratory OR lab OR PhD OR postdoc',
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _marker_terms(opportunity_type: str | None) -> tuple[str, ...]:
    return {
        "Job": ("job", "career", "vacancy", "position", "employment"),
        "Internship": ("intern", "internship", "trainee", "placement", "working student"),
        "Master's": ("master", "msc", "admission", "graduate program", "degree program", "postgraduate"),
        "Scholarship": ("scholarship", "fellowship", "funding", "stipend", "grant", "tuition waiver", "financial aid"),
        "Research": ("research", "professor", "laboratory", "lab", "phd", "postdoc", "research assistant"),
    }.get(opportunity_type or "", ())


def _looks_relevant(title: str, snippet: str, url: str, opportunity_type: str | None) -> bool:
    hay = f"{title} {snippet} {url}".lower()
    markers = _marker_terms(opportunity_type)
    if not markers:
        return True
    return any(marker in hay for marker in markers)


def _organization(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    return host or "Unknown organization"


class GoogleWebSource(BaseSource):
    """Global web discovery backed by Google results.

    Preferred backend: Serper (real-time Google Search results).
    Optional backend: Google Custom Search JSON API for existing customers.
    """

    name = "Google Web Discovery"

    def __init__(self, serper_api_key: str | None = None, google_api_key: str | None = None, google_cse_id: str | None = None):
        self.serper_api_key = serper_api_key or SERPER_API_KEY
        self.google_api_key = google_api_key or GOOGLE_API_KEY
        self.google_cse_id = google_cse_id or GOOGLE_CSE_ID

    @property
    def configured(self) -> bool:
        return bool(GEMINI_API_KEY or self.serper_api_key or (self.google_api_key and self.google_cse_id))

    def _build_query(self, query: str, opportunity_type: str | None, country: str | None) -> str:
        q = (query or "").strip()
        if opportunity_type in TYPE_TERMS:
            q = f"{q} ({TYPE_TERMS[opportunity_type]})"
        if country:
            q = f"{q} {country}"
        return _clean(q)

    async def _fetch_page(self, client: httpx.AsyncClient, url: str) -> tuple[str, str]:
        try:
            response = await client.get(url)
            if response.status_code >= 400:
                return "", str(response.url)
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                return "", str(response.url)
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
                tag.decompose()
            return _clean(soup.get_text(" ", strip=True))[:24000], str(response.url)
        except Exception:
            return "", url


    async def _gemini_google_search(self, client: httpx.AsyncClient, q: str, opportunity_type: str | None, country: str | None) -> list[dict]:
        """Use Gemini's native Google Search grounding to retrieve live public-web sources.

        Google handles the search itself and returns grounding chunks containing the
        actual source URLs. We then fetch those pages independently so Opportune's
        normal requirement extraction and verification pipeline still applies.
        """
        prompt = f"""
Search Google for real, currently available {opportunity_type or 'opportunities'} on the public web.
Search broadly across universities, employers, scholarship providers, research labs,
government sites, official organizations, and reputable opportunity databases.
Do not invent opportunities. Prefer direct opportunity/admission/application pages.
Query: {q}
Country: {country or 'any country'}
Return a short summary only; the application will use Google's grounded source URLs.
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
        }
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return []
        metadata = candidates[0].get("groundingMetadata") or {}
        chunks = metadata.get("groundingChunks") or []
        out = []
        seen = set()
        for chunk in chunks:
            web = chunk.get("web") or {}
            url = web.get("uri") or ""
            title = _clean(web.get("title") or "")
            if url and title and url not in seen:
                seen.add(url)
                out.append({"link": url, "title": title, "snippet": "Google Search grounded source"})
        return out

    async def _serper(self, client: httpx.AsyncClient, q: str, country: str | None) -> list[dict]:
        payload = {
            "q": q,
            "num": 10,
            "autocorrect": True,
        }
        # Serper supports Google-style country localization.
        if country:
            payload["gl"] = country[:2].lower() if len(country) == 2 else country.lower()
        response = await client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": self.serper_api_key, "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("organic", []) or []

    async def _google_cse(self, client: httpx.AsyncClient, q: str, country: str | None) -> list[dict]:
        params = {
            "key": self.google_api_key,
            "cx": self.google_cse_id,
            "q": q,
            "num": 10,
            "filter": "1",
        }
        if country and len(country) == 2:
            params["gl"] = country.lower()
        response = await client.get("https://www.googleapis.com/customsearch/v1", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("items", []) or []

    async def search(self, query: str, opportunity_type: str | None = None, country: str | None = None) -> list[Opportunity]:
        if not self.configured:
            return []

        q = self._build_query(query, opportunity_type, country)
        try:
            async with httpx.AsyncClient(
                timeout=25,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; OpportuneAI/1.0)"},
            ) as client:
                # Prefer Google's native Search grounding when a Gemini key exists.
                # This is the most direct Google-powered route and needs no separate
                # search-engine scraping. Serper and legacy CSE remain fallbacks.
                if GEMINI_API_KEY:
                    raw_results = await self._gemini_google_search(client, q, opportunity_type, country)
                elif self.serper_api_key:
                    raw_results = await self._serper(client, q, country)
                else:
                    raw_results = await self._google_cse(client, q, country)

                candidates = []
                seen = set()
                for raw in raw_results:
                    url = raw.get("link") or raw.get("url") or ""
                    title = _clean(raw.get("title") or "")
                    snippet = _clean(raw.get("snippet") or raw.get("description") or "")
                    if not url or not title or url in seen:
                        continue
                    if url.startswith("http"):
                        seen.add(url)
                        candidates.append((title, snippet, url))

                async def process(title: str, snippet: str, url: str):
                    if not _looks_relevant(title, snippet, url, opportunity_type):
                        return None
                    text, final_url = await self._fetch_page(client, url)
                    combined = _clean(f"{title}. {snippet}. {text}")
                    # Do not require every query token to be present on the page.
                    # Search engines already did relevance ranking; this layer only
                    # rejects obviously unrelated pages.
                    if not _looks_relevant(title, combined[:16000], final_url, opportunity_type):
                        return None
                    requirements = extract_requirements(text or snippet)
                    skills = extract_required_skills(text or snippet)
                    return Opportunity(
                        title=title,
                        organization=_organization(final_url),
                        opportunity_type=opportunity_type or "UNKNOWN",
                        country=country,
                        description=(text or snippet)[:6000],
                        requirements=requirements,
                        application_url=final_url,
                        source_url=final_url,
                        source_name=self.name,
                        verification_status="UNVERIFIED",
                        metadata={
                            "discovery_type": "GOOGLE_SEARCH",
                            "search_query": q,
                            "search_snippet": snippet,
                            "destination_url": final_url,
                            "required_skills": skills,
                        },
                    )

                results = await asyncio.gather(*(process(*candidate) for candidate in candidates))
                return [item for item in results if item]
        except Exception:
            return []
