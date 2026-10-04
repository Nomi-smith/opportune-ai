import re
from urllib.parse import urlparse

COLLECTION_PATTERNS = (
    r'\b\d+\s+(?:fully funded\s+)?(?:scholarships?|fellowships?|grants?|programs?|masters?|master\'s)\b',
    r'\b(?:top|best|list of|guide to|roundup of|collection of)\b',
    r'\b\d+\s+(?:ways|opportunities|options)\b',
)
LEAD_PATTERNS = (
    r'\b(?:blog|news|article|guide|how to|explained|overview|what is)\b',
)
ACTION_PATTERNS = (
    'apply now','apply here','application portal','apply online','applications open',
    'applications are open','accepting applications','open for applications',
    'deadline','application deadline','apply by','closing date','open until filled',
    'rolling admissions','rolling applications','ongoing'
)

def _text(item):
    meta=getattr(item,'metadata',{}) or {}
    return ' '.join(str(x or '') for x in [getattr(item,'title',''), getattr(item,'description',''), meta.get('summary'), meta.get('search_snippet')])

def source_tier(url, source_name=''):
    host=urlparse(url or '').netloc.lower()
    if any(x in host for x in ('.gov', '.gov.', '.edu', '.ac.', '.edu.', '.ac.uk', '.gov.uk')):
        return 'official'
    if host.endswith('.org'):
        return 'organization'
    if source_name and any(x in source_name.lower() for x in ('arbeitnow','openalex')):
        return 'database'
    return 'web'

def classify_page(item):
    title=str(getattr(item,'title','') or '')
    text=_text(item).lower()
    compact=(title+' '+text[:4000]).lower()
    if any(re.search(p, compact, re.I) for p in COLLECTION_PATTERNS):
        return 'collection'
    if any(re.search(p, compact, re.I) for p in LEAD_PATTERNS) and not any(x in compact for x in ACTION_PATTERNS):
        return 'lead'
    if any(x in compact for x in ACTION_PATTERNS):
        return 'opportunity'
    return 'unknown'

def annotate_quality(item):
    meta=dict(getattr(item,'metadata',{}) or {})
    cls=classify_page(item)
    tier=source_tier(getattr(item,'source_url','') or getattr(item,'application_url',''), getattr(item,'source_name',''))
    meta['page_class']=cls
    meta['source_tier']=tier
    meta['quality_status']='candidate'
    meta['quality_reason']=('Specific actionable page signals detected.' if cls=='opportunity' else
                            'Collection/list page; not treated as a single opportunity.' if cls=='collection' else
                            'Informational/lead page; not treated as an actionable opportunity.' if cls=='lead' else
                            'No strong action signal yet; requires source-page verification.')
    item.metadata=meta
    return item

def quality_filter(items, include_unverified=False):
    kept=[]
    for item in items:
        annotate_quality(item)
        cls=item.metadata.get('page_class')
        if cls in {'collection','lead'}:
            continue
        if cls=='unknown' and not include_unverified:
            # Search results can be retained when they have a direct application URL.
            url=getattr(item,'application_url','') or getattr(item,'source_url','')
            if not url:
                continue
        kept.append(item)
    return kept
