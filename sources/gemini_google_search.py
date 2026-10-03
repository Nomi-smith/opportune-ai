import asyncio
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config.settings import GEMINI_API_KEY
from intelligence.requirements import extract_required_skills, extract_requirements
from models.opportunity import Opportunity
from sources.base import BaseSource


class GeminiGoogleSearchSource(BaseSource):
    name = "Google Search (Gemini Grounding)"

    def __init__(self, api_key: str | None = None, model: str = "gemini-3.8-flash"):
        self.api_key = api_key or GEMINI_API_KEY
        self.model = model
        self.last_error = ""

    @staticmethod
    def _domain(url):
        try:
            host = urlparse(url).netloc.lower()
            return host[4:] if host.startswith("www.") else host
        except Exception:
            return ""

    async def _fetch_page(self, client, url):
        try:
            response = await client.get(url, follow_redirects=True)
            if response.status_code >= 400:
                return "", str(response.url)
            if "text/html" not in response.headers.get("content-type", ""):
                return "", str(response.url)
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text("\n", strip=True)
            return re.sub(r"\n{3,}", "\n\n", text)[:24000], str(response.url)
        except Exception:
            return "", url

    async def search(self, query: str, opportunity_type: str | None = None, country: str | None = None):
        self.last_error = ""
        if not self.api_key:
            self.last_error = "GEMINI_API_KEY is not configured"
            return []

        q = (query or "").strip()
        if opportunity_type and opportunity_type != "All":
            q += f" {opportunity_type}"
        if country:
            q += f" {country}"
        prompt = f"""Search Google for real, current public-web opportunity pages matching this request:\n{q}\n\nUse Google Search. Prefer direct official pages from universities, governments, employers, research labs, foundations, or official program pages. Do not answer from memory. Find multiple distinct source pages."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "tools": [{"google_search": {}}],
        }
        try:
            async with httpx.AsyncClient(timeout=45) as client:
                response = await client.post(url, params={"key": self.api_key}, json=payload)
            if response.status_code >= 400:
                self.last_error = f"Gemini HTTP {response.status_code}: {response.text[:700]}"
                return []
            data = response.json()
        except Exception as exc:
            self.last_error = f"Gemini request failed: {exc}"
            return []

        chunks = []
        for candidate in data.get("candidates") or []:
            gm = candidate.get("groundingMetadata") or {}
            chunks.extend(gm.get("groundingChunks") or [])
        seen = set()
        candidates = []
        for chunk in chunks:
            web = chunk.get("web") or {}
            uri = web.get("uri")
            title = web.get("title") or self._domain(uri)
            if not uri or not uri.startswith(("http://", "https://")):
                continue
            key = uri.split("#", 1)[0]
            if key in seen:
                continue
            seen.add(key)
            candidates.append((title, key))
        if not candidates:
            self.last_error = self.last_error or "Gemini returned no grounded web sources"
            return []

        async with httpx.AsyncClient(timeout=25, headers={"User-Agent": "OpportuneAI/0.5"}, follow_redirects=True) as client:
            pages = await asyncio.gather(*(self._fetch_page(client, url) for _, url in candidates[:12]))

        results = []
        for (title, url), (text, final_url) in zip(candidates[:12], pages):
            body = text
            if not body:
                continue
            kind = (opportunity_type or "UNKNOWN").upper()
            results.append(Opportunity(
                title=str(title)[:300],
                organization=self._domain(final_url or url) or "Web source",
                opportunity_type=kind,
                country=country or None,
                description=body[:9000],
                requirements=extract_requirements(body),
                application_url=final_url or url,
                source_url=final_url or url,
                source_name=self.name,
                verification_status="UNVERIFIED",
                metadata={
                    "discovery_type": "GOOGLE_SEARCH_GROUNDING",
                    "search_query": q,
                    "destination_url": final_url or url,
                    "required_skills": extract_required_skills(body),
                },
            ))
        return results
