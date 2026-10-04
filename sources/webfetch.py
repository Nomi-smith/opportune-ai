import httpx
from intelligence.source_content import clean_source_html

async def fetch_url(url: str, timeout: float = 5.0, max_chars: int = 30000) -> str:
    if not url or not url.startswith(("http://", "https://")):
        return ""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OpportuneAI/1.0; public research)"}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type and "xhtml" not in content_type:
                return ""
            return clean_source_html(response.text, max_chars=max_chars)
    except Exception:
        return ""


async def fetch_html(url: str, timeout: float = 6.0, max_chars: int = 400000) -> str:
    """Raw HTML of a page (links intact). fetch_url returns cleaned text, which has no links."""
    if not url or not url.startswith(("http://", "https://")):
        return ""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OpportuneAI/1.0; public research)"}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            if "html" not in response.headers.get("content-type", "").lower():
                return ""
            return response.text[:max_chars]
    except Exception:
        return ""


def extract_page_title(html_text: str) -> tuple[str, str]:
    """(title, site_name) from og:title / <title> / <h1>, with the trailing '| Site' suffix removed."""
    import re
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text or "", "html.parser")

    def meta(prop):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        return (tag.get("content") or "").strip() if tag else ""
    site = meta("og:site_name")
    raw = meta("og:title") or (soup.title.get_text(" ", strip=True) if soup.title else "")
    if not raw:
        h1 = soup.find("h1")
        raw = h1.get_text(" ", strip=True) if h1 else ""
    raw = re.sub(r"\s+", " ", raw).strip()
    parts = re.split(r"\s+[|\u2013\u2014-]\s+", raw)
    title = parts[0] if parts and len(parts[0]) >= 15 else raw
    if not site and len(parts) > 1 and len(parts[-1]) <= 40:
        site = parts[-1]
    return title[:200], site[:80]


def extract_h1(html_text: str) -> str:
    """First visible <h1>: usually the real opportunity name, even when <title> is just the site section."""
    import re
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text or "", "html.parser")
    for h1 in soup.find_all("h1"):
        text = re.sub(r"\s+", " ", h1.get_text(" ", strip=True)).strip()
        if len(text) >= 8:
            return text[:200]
    return ""


def extract_page_signals(html_text: str) -> dict:
    """Machine-readable facts a page publishes about itself: meta description and JobPosting dates."""
    import json
    import re
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_text or "", "html.parser")
    out = {"description": "", "valid_through": "", "date_posted": "", "robots_noindex": False}
    for key in ({"property": "og:description"}, {"name": "description"}):
        tag = soup.find("meta", attrs=key)
        if tag and (tag.get("content") or "").strip():
            out["description"] = re.sub(r"\s+", " ", tag["content"]).strip()[:500]
            break

    def walk(node):
        if isinstance(node, list):
            for x in node:
                yield from walk(x)
        elif isinstance(node, dict):
            yield node
            for v in node.values():
                if isinstance(v, (list, dict)):
                    yield from walk(v)
    for tag in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(tag.string or tag.get_text() or "null")
        except Exception:
            continue
        for node in walk(data):
            kind = node.get("@type")
            kinds = kind if isinstance(kind, list) else [kind]
            if "JobPosting" in kinds or "Scholarship" in kinds or "EducationalOccupationalProgram" in kinds:
                out["valid_through"] = out["valid_through"] or str(node.get("validThrough") or node.get("applicationDeadline") or "")[:40]
                out["date_posted"] = out["date_posted"] or str(node.get("datePosted") or "")[:40]
    robots = soup.find("meta", attrs={"name": "robots"})
    if robots and "noindex" in (robots.get("content") or "").lower():
        out["robots_noindex"] = True
    return out


async def fetch_page(url: str, timeout: float = 8.0, max_chars: int = 12000) -> dict:
    """One request -> {'title','site','h1','text','description','valid_through','date_posted'}.
    text is cleaned of menus/footers. Empty dict on failure (404/410, timeouts, non-HTML)."""
    if not url or not url.startswith(("http://", "https://")):
        return {}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OpportuneAI/1.0; public research)"}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
            if "html" not in response.headers.get("content-type", "").lower():
                return {}
            html = response.text[:400000]
            title, site = extract_page_title(html)
            page = {"title": title, "site": site, "h1": extract_h1(html),
                    "text": clean_source_html(html, max_chars=max_chars), "final_url": str(response.url)}
            page.update(extract_page_signals(html))
            return page
    except Exception:
        return {}
