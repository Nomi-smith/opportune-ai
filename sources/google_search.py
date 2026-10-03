import asyncio
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config.settings import GEMINI_API_KEY
from intelligence.requirements import extract_required_skills, extract_requirements
from models.opportunity import Opportunity
from sources.base import BaseSource


class GoogleGroundedSource(BaseSource):
    """Live Google Search through Gemini's official Google Search grounding tool."""

    name = "Google Search (Gemini Grounding)"
    MODEL = "gemini-3.8-flash"
    API_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent"
    )

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or GEMINI_API_KEY
        self.last_error = ""
        self.last_queries: list[str] = []

    @staticmethod
    def _clean_html(html: str) -> str:
        soup = BeautifulSoup(html or "", "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text("\n", strip=True)[:24000]

    async def _fetch(self, client: httpx.AsyncClient, url: str):
        try:
            response = await client.get(url, follow_redirects=True)
            if response.status_code >= 400:
                return "", str(response.url)
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                return "", str(response.url)
            return self._clean_html(response.text), str(response.url)
        except Exception:
            return "", url

    async def search(self, query, opportunity_type=None, country=None):
        self.last_error = ""
        self.last_queries = []

        if not self.api_key:
            self.last_error = "GEMINI_API_KEY is not configured."
            return []

        query = (query or "").strip()
        if country:
            query = f"{query} {country}".strip()

        type_instruction = {
            "Scholarship": "actual scholarship, fellowship, grant, tuition waiver, or funding opportunity",
            "Master's": "actual master's degree program or admissions page",
            "Research": "actual research opportunity, research position, laboratory, research group, or professor opportunity",
            "Internship": "actual internship or working-student opportunity",
            "Job": "actual job or vacancy",
            "All": "actual opportunity",
        }.get(opportunity_type or "All", "actual opportunity")

        prompt = f"""
Search the live public web with Google for this opportunity request.
Request: {query}
Opportunity type: {opportunity_type or 'All'}
Country: {country or 'any country'}

Find {type_instruction} pages.
Search broadly. Prefer official university, government, company, research-lab,
scholarship-provider, organization, or program pages. Aggregators may be used
as secondary sources. Do not invent opportunities or URLs.
Return enough grounded web sources for an application/discovery system to inspect.
""".strip()

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    self.API_URL,
                    headers={
                        "x-goog-api-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                if response.status_code >= 400:
                    self.last_error = f"Gemini HTTP {response.status_code}: {response.text[:1000]}"
                    return []
                data = response.json()
        except Exception as exc:
            self.last_error = f"Gemini Search request failed: {exc}"
            return []

        candidate = (data.get("candidates") or [{}])[0]
        metadata = candidate.get("groundingMetadata") or candidate.get("grounding_metadata") or {}
        self.last_queries = (
            metadata.get("webSearchQueries")
            or metadata.get("web_search_queries")
            or []
        )
        chunks = metadata.get("groundingChunks") or metadata.get("grounding_chunks") or []

        # Gemini's generateContent REST response exposes grounded sources here.
        source_urls = []
        for chunk in chunks:
            web = chunk.get("web") or {}
            uri = web.get("uri")
            title = web.get("title") or ""
            if uri:
                source_urls.append((title, uri))

        unique = []
        seen = set()
        for title, uri in source_urls:
            if uri in seen:
                continue
            seen.add(uri)
            unique.append((title, uri))

        if not unique:
            self.last_error = self.last_error or (
                "Gemini Search returned no grounded web sources. "
                f"Executed queries: {self.last_queries or 'none reported'}"
            )
            return []

        async with httpx.AsyncClient(
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (compatible; OpportuneAI/1.0)"},
            follow_redirects=True,
        ) as client:
            fetched = await asyncio.gather(
                *(self._fetch(client, uri) for _, uri in unique[:30])
            )

        results = []
        for (source_title, source_uri), (text, final_url) in zip(unique[:30], fetched):
            if not text:
                continue

            page_title = source_title
            try:
                parsed = BeautifulSoup(text, "html.parser")
                if parsed.title and parsed.title.get_text(strip=True):
                    page_title = parsed.title.get_text(" ", strip=True)[:250]
            except Exception:
                pass

            host = urlparse(final_url).netloc.lower().removeprefix("www.") or "Unknown"
            requirements = extract_requirements(text)
            skills = extract_required_skills(text)
            results.append(
                Opportunity(
                    title=page_title or source_title or "Untitled opportunity",
                    organization=host,
                    opportunity_type=(opportunity_type or "UNKNOWN").upper(),
                    country=country or None,
                    description=text[:6000],
                    requirements=requirements,
                    application_url=final_url,
                    source_url=final_url,
                    source_name=self.name,
                    verification_status="UNVERIFIED",
                    metadata={
                        "discovery_type": "GOOGLE_GROUNDED",
                        "google_search_queries": self.last_queries,
                        "google_source_title": source_title,
                        "destination_url": final_url,
                        "required_skills": skills,
                    },
                )
            )

        if not results and not self.last_error:
            self.last_error = "Google returned grounded sources, but none of the destination pages could be fetched."
        return results
