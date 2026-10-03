import json
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config.settings import OPENROUTER_API_KEY, OPENROUTER_SEARCH_ENGINE, OPENROUTER_SEARCH_MODEL
from intelligence.requirements import extract_required_skills, extract_requirements
from models.opportunity import Opportunity
from sources.base import BaseSource


SEARCH_TIMEOUT = 45
MAX_RESULTS = 10


def _domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _clean(value: str) -> str:
    soup = BeautifulSoup(str(value or ""), "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def _extract_urls(data: dict) -> list[tuple[str, str, str]]:
    """Extract search-result URLs from OpenRouter's annotations and text.

    OpenRouter's web_search server tool returns titles/URLs/snippets to the model.
    Response shapes can evolve, so this parser intentionally accepts several forms.
    """
    out, seen = [], set()

    def add(title, url, snippet=""):
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return
        host = _domain(url)
        if not host or host in {"openrouter.ai", "ai.google.dev"}:
            return
        key = url.split("#", 1)[0]
        if key in seen:
            return
        seen.add(key)
        out.append((_clean(title) or host, key, _clean(snippet)))

    choices = data.get("choices") or []
    for choice in choices:
        message = choice.get("message") or {}
        # Newer response annotations.
        for ann in message.get("annotations") or []:
            if not isinstance(ann, dict):
                continue
            url_citation = ann.get("url_citation") or ann.get("url") or {}
            if isinstance(url_citation, dict):
                add(url_citation.get("title"), url_citation.get("url"), url_citation.get("snippet", ""))
            elif isinstance(url_citation, str):
                add("Web result", url_citation, "")

        # Some providers expose tool results in message content.
        content = message.get("content", "")
        if isinstance(content, list):
            content = " ".join(str(x.get("text", "")) for x in content if isinstance(x, dict))
        text = str(content or "")
        for m in re.finditer(r"\[([^\]]{2,200})\]\((https?://[^)\s]+)\)", text):
            add(m.group(1), m.group(2), "")
        for m in re.finditer(r"(?im)^\s*(?:title\s*:\s*)?(.{3,180}?)\s*[-–—|]\s*(https?://\S+)", text):
            add(m.group(1), m.group(2).rstrip(".,)"), "")

    # Last-resort recursive scan for URL-bearing result objects.
    def walk(obj):
        if isinstance(obj, dict):
            url = obj.get("url") or obj.get("link")
            title = obj.get("title") or obj.get("name") or "Web result"
            snippet = obj.get("snippet") or obj.get("description") or obj.get("text") or ""
            if url:
                add(title, url, snippet)
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
    walk(data)
    return out[:MAX_RESULTS]


class OpenRouterWebSearchSource(BaseSource):
    name = "OpenRouter Web Search"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.last_error = ""

    async def _fetch_page(self, client, url: str):
        try:
            response = await client.get(url, follow_redirects=True)
            if response.status_code >= 400:
                return "", str(response.url)
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
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
            self.last_error = "OPENROUTER_API_KEY is not configured"
            return []

        q = (query or "").strip()
        if opportunity_type and opportunity_type != "All":
            q += f" {opportunity_type}"
        if country:
            q += f" {country}"
        q += " official university company organization application admissions scholarship fellowship research opportunity"

        prompt = f"""Search the public web for real, currently relevant opportunity pages for this request:\n{q}\n\nMANDATORY: use the web search tool. Return the most useful direct source pages, not search-engine result pages. Prefer official university, government, company, research-lab, foundation, or employer pages. Return concise titles and URLs in your answer."""
        payload = {
            "model": OPENROUTER_SEARCH_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "tools": [{
                "type": "openrouter:web_search",
                "parameters": {
                    "engine": OPENROUTER_SEARCH_ENGINE or "auto",
                    "max_results": 10,
                    "max_total_results": 10,
                    "max_uses": 2,
                    "search_context_size": "medium",
                },
            }],
            "max_tool_calls": 3,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://opportune-ai.local",
            "X-Title": "Opportune AI",
        }
        try:
            async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT) as client:
                response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            if response.status_code >= 400:
                self.last_error = f"OpenRouter HTTP {response.status_code}: {response.text[:500]}"
                return []
            data = response.json()
        except Exception as exc:
            self.last_error = f"OpenRouter request failed: {exc}"
            return []

        candidates = _extract_urls(data)
        if not candidates:
            self.last_error = "OpenRouter returned no extractable web URLs"
            return []

        async with httpx.AsyncClient(timeout=25, headers={"User-Agent": "OpportuneAI/0.5"}, follow_redirects=True) as client:
            fetched = await __import__("asyncio").gather(*(self._fetch_page(client, url) for _, url, _ in candidates))

        results = []
        for (title, url, snippet), (text, final_url) in zip(candidates, fetched):
            body = text or snippet
            if not body:
                continue
            kind = (opportunity_type or "UNKNOWN").upper()
            if kind == "MASTER'S":
                kind = "MASTER'S"
            elif kind in {"JOB", "INTERNSHIP", "SCHOLARSHIP", "RESEARCH"}:
                pass
            else:
                kind = "UNKNOWN"
            host = _domain(final_url or url) or "Web source"
            description = body[:8000]
            results.append(Opportunity(
                title=title[:300],
                organization=host,
                opportunity_type=kind,
                country=country or None,
                description=description,
                requirements=extract_requirements(description),
                application_url=final_url or url,
                source_url=final_url or url,
                source_name=self.name,
                verification_status="UNVERIFIED",
                metadata={
                    "discovery_type": "OPENROUTER_WEB_SEARCH",
                    "search_query": q,
                    "snippet": snippet[:1000],
                    "destination_url": final_url or url,
                    "required_skills": extract_required_skills(description),
                },
            ))
        return results
