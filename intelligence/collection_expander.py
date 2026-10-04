import asyncio
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from models.opportunity import Opportunity
from sources.webfetch import fetch_html
from intelligence.freshness import filter_current_opportunities
from intelligence.opportunity_quality import annotate_quality

MARKERS = {
    'Scholarship': ('scholarship','fellowship','grant','funding','award','apply'),
    "Master's": ('master','msc','admission','apply','program','programme'),
    'Research': ('research','professor','lab','laboratory','position','phd'),
}

async def expand_collection(item, opportunity_type, max_links=5):
    url=getattr(item,'application_url','') or getattr(item,'source_url','')
    if not url: return []
    html=await fetch_html(url, timeout=6)
    if not html: return []
    soup=BeautifulSoup(html,'html.parser')
    base_host=urlparse(url).netloc.lower()
    markers=MARKERS.get(opportunity_type, ())
    candidates=[]; seen=set()
    for a in soup.find_all('a', href=True):
        href=urljoin(url, a.get('href',''))
        if not href.startswith(('http://','https://')): continue
        if urlparse(href).netloc.lower()!=base_host: continue
        title=' '.join(a.get_text(' ', strip=True).split())
        if len(title)<10 or len(title)>180: continue
        low=(title+' '+href).lower()
        if not any(m in low for m in markers): continue
        if href in seen or href==url: continue
        seen.add(href)
        candidates.append(Opportunity(
            id=f'expanded:{href}', title=title, organization=getattr(item,'organization','') or '',
            opportunity_type=(opportunity_type or 'UNKNOWN').upper(), country=getattr(item,'country',None),
            description=f'Extracted from a current opportunity collection page: {url}',
            application_url=href, source_url=href, source_name='Collection expansion',
            metadata={'parent_collection_url':url,'expanded_from_collection':True}
        ))
        if len(candidates)>=max_links: break
    current=filter_current_opportunities(candidates)
    return [annotate_quality(x) for x in current]

async def expand_collections(items, opportunity_type, max_pages=2, max_links=5):
    if opportunity_type not in {'Scholarship', "Master's", 'Research'} or not items:
        return []
    collections=[x for x in items if (getattr(x,'metadata',{}) or {}).get('page_class')=='collection'][:max_pages]
    if not collections: return []
    batches=await asyncio.gather(*(expand_collection(x, opportunity_type, max_links) for x in collections), return_exceptions=True)
    out=[]
    for batch in batches:
        if isinstance(batch, list): out.extend(batch)
    return out
