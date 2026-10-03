import asyncio
import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
import httpx
from bs4 import BeautifulSoup
from intelligence.requirements import extract_required_skills, extract_requirements
from models.opportunity import Opportunity
from sources.base import BaseSource

SEARCH_ENGINE_HOSTS = {'duckduckgo.com','www.duckduckgo.com','google.com','www.google.com','bing.com','www.bing.com','search.yahoo.com'}
GENERIC_HOSTS = {'linkedin.com','www.linkedin.com','indeed.com','www.indeed.com','glassdoor.com','www.glassdoor.com','jooble.org','www.jooble.org'}
LISTING_MARKERS = ('/jobs/search','/job-search','/search/jobs','/jobs/collections','/jobs/browse','/opportunities/search','/internships/search','/scholarships/search','/search/results')


def unwrap_search_url(href: str) -> str:
    if not href: return ''
    if href.startswith('//'): href = 'https:' + href
    p = urlparse(href)
    if p.netloc.lower() not in SEARCH_ENGINE_HOSTS: return href
    qs = parse_qs(p.query)
    for key in ('uddg','url','q'):
        if qs.get(key): return unquote(qs[key][0])
    return ''


def is_listing_page(url: str) -> bool:
    p = urlparse(url); full = ((p.path or '') + '?' + (p.query or '')).lower()
    if any(x in full for x in LISTING_MARKERS): return True
    if p.netloc.lower() in GENERIC_HOSTS and any(x in (p.path or '').lower() for x in ('/jobs','/job','/search')):
        return not any(x in (p.path or '').lower() for x in ('/view/','/viewjob','/posting/','/job/view','/jobs/view'))
    return False


def _intent_tokens(query: str) -> list[str]:
    raw = [x for x in (query or '').lower().replace('-', ' ').split() if len(x) > 1]
    groups = []
    for token in raw:
        if token in ('ai','artificial','intelligence'): groups.append('ai')
        elif token in ('intern','internship','trainee','student'): groups.append('intern')
        elif token in ('ml','machine','learning'): groups.append('ml')
        elif token in ('software','developer','development','engineer','engineering'): groups.append('software')
        elif token in ('research','researcher','phd','doctoral','postdoc','professor'): groups.append('research')
        else: groups.append(token)
    return list(dict.fromkeys(groups))


def _relevant(query: str, title: str, text: str) -> bool:
    # Search engines already perform relevance ranking. Do not require every
    # query token to occur verbatim: universities and international pages often
    # use local terminology or omit a keyword from the page title.
    groups = _intent_tokens(query)
    hay = (title + " " + text[:16000]).lower()
    if not groups:
        return True
    aliases = {
        'ai': ('ai', 'artificial intelligence', 'machine intelligence', 'machine learning', 'computer vision'),
        'intern': ('intern', 'internship', 'trainee', 'student', 'placement', 'working student'),
        'ml': ('machine learning', 'ml', 'deep learning', 'artificial intelligence'),
        'software': ('software', 'developer', 'development', 'engineer', 'engineering', 'computer science'),
        'research': ('research', 'researcher', 'phd', 'doctoral', 'postdoc', 'professor', 'laboratory', 'lab'),
    }
    hits = sum(1 for g in groups if any(v in hay for v in aliases.get(g, (g,))))
    # One strong signal is enough for broad discovery; type filtering happens later.
    return hits >= 1


class PublicWebSource(BaseSource):
    name = 'Public Web Discovery'

    async def _fetch_page(self, client, url: str):
        try:
            response = await client.get(url)
            if response.status_code >= 400: return '', str(response.url)
            if 'text/html' not in response.headers.get('content-type',''): return '', str(response.url)
            soup = BeautifulSoup(response.text, 'html.parser')
            for tag in soup(['script','style','noscript','svg','nav','footer','header']): tag.decompose()
            return soup.get_text('\n', strip=True)[:20000], str(response.url)
        except Exception:
            return '', url

    async def search(self, query: str, opportunity_type: str | None = None, country: str | None = None):
        q = (query or '').strip()
        search_query = q
        if opportunity_type and opportunity_type != 'All': search_query += f' {opportunity_type}'
        if country: search_query += f' {country}'
        search_query += ' (apply OR internship OR job OR scholarship OR fellowship OR admissions OR phd)'
        url = 'https://html.duckduckgo.com/html/?q=' + quote_plus(search_query)
        try:
            async with httpx.AsyncClient(timeout=20, headers={'User-Agent':'OpportuneAI/0.4'}, follow_redirects=True) as client:
                response = await client.get(url); response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                candidates=[]; seen=set()
                for result in soup.select('.result')[:40]:
                    a=result.select_one('.result__a')
                    if not a: continue
                    href=unwrap_search_url(a.get('href',''))
                    if not href or href in seen: continue
                    p=urlparse(href)
                    if not p.netloc or p.netloc.lower() in SEARCH_ENGINE_HOSTS or is_listing_page(href): continue
                    seen.add(href)
                    candidates.append((a.get_text(' ',strip=True),href))
                async def process(title, href):
                    text, final_url = await self._fetch_page(client, href)
                    if not text or is_listing_page(final_url) or not _relevant(q,title,text): return None
                    marker=(title+' '+text[:12000]).lower()
                    signals = {
                        'job': ('job','career','vacancy','position','employment','apply'),
                        'internship': ('intern','internship','trainee','working student','placement'),
                        "master's": ('master','msc','m.sc','admission','graduate programme','graduate program','degree programme','degree program'),
                        'scholarship': ('scholarship','fellowship','grant','funding','tuition waiver','financial aid','stipend'),
                        'research': ('research','professor','research group','laboratory','lab','phd','doctoral','postdoc'),
                    }
                    key=(opportunity_type or '').lower()
                    if key in signals and not any(x in marker for x in signals[key]):
                        return None
                    req=extract_requirements(text); skills=extract_required_skills(text)
                    host=urlparse(final_url).netloc.lower()
                    return Opportunity(title=title, organization=host, opportunity_type=(opportunity_type if opportunity_type and opportunity_type!='All' else 'UNKNOWN'), description=re.sub(r'<[^>]+>', ' ', text[:5000]).strip(), requirements=req, application_url=final_url, source_url=final_url, source_name=self.name, verification_status='UNVERIFIED', metadata={'discovery_type':'DIRECT_PAGE','destination_url':final_url,'required_skills':skills})
                results=await asyncio.gather(*(process(t,u) for t,u in candidates))
                return [x for x in results if x]
        except Exception:
            return []
