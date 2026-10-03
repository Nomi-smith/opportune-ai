import asyncio
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config.settings import SERPER_API_KEY
from intelligence.requirements import extract_required_skills, extract_requirements
from models.opportunity import Opportunity
from sources.base import BaseSource


class SerperGoogleSource(BaseSource):
    name = "Google Search (Serper)"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or SERPER_API_KEY
        self.last_error = ""

    @staticmethod
    def _domain(url):
        try:
            host = urlparse(url).netloc.lower()
            return host[4:] if host.startswith("www.") else host
        except Exception:
            return ""

    async def _fetch(self, client, url):
        try:
            r = await client.get(url, follow_redirects=True)
            if r.status_code >= 400 or "text/html" not in r.headers.get("content-type", ""):
                return "", str(r.url)
            soup = BeautifulSoup(r.text, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg", "nav", "footer", "header"]):
                tag.decompose()
            return re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))[:24000], str(r.url)
        except Exception:
            return "", url

    async def search(self, query, opportunity_type=None, country=None):
        self.last_error = ""
        if not self.api_key:
            return []
        q = (query or "").strip()
        if opportunity_type and opportunity_type != "All": q += f" {opportunity_type}"
        if country: q += f" {country}"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                r = await client.post("https://google.serper.dev/search", headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"}, json={"q": q, "num": 10})
            if r.status_code >= 400:
                self.last_error = f"Serper HTTP {r.status_code}: {r.text[:500]}"
                return []
            organic = r.json().get("organic") or []
        except Exception as exc:
            self.last_error = f"Serper request failed: {exc}"
            return []
        candidates = []
        seen=set()
        for item in organic:
            url=item.get("link")
            if not url or url in seen: continue
            seen.add(url); candidates.append((item.get("title") or self._domain(url), url, item.get("snippet") or ""))
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent":"OpportuneAI/0.5"}, follow_redirects=True) as client:
            pages=await asyncio.gather(*(self._fetch(client,u) for _,u,_ in candidates))
        out=[]
        for (title,url,snippet),(text,final_url) in zip(candidates,pages):
            body=text or snippet
            if not body: continue
            kind=(opportunity_type or "UNKNOWN").upper()
            out.append(Opportunity(title=title[:300],organization=self._domain(final_url or url),opportunity_type=kind,country=country or None,description=body[:9000],requirements=extract_requirements(body),application_url=final_url or url,source_url=final_url or url,source_name=self.name,verification_status="UNVERIFIED",metadata={"discovery_type":"SERPER_GOOGLE","search_query":q,"destination_url":final_url or url,"required_skills":extract_required_skills(body)}))
        return out
