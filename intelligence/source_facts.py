"""Conservative extraction of facts from the actual opportunity source page."""
from __future__ import annotations
import re
from datetime import datetime

NA = "N/A"


def _clean(v):
    v = re.sub(r'\s+', ' ', str(v or '')).strip(' :;-–—')
    return v[:260]


def _label(text, labels, max_len=260):
    if not text: return None
    pattern = r'(?i)(?:' + '|'.join(re.escape(x) for x in labels) + r')\s*[:\-–—]\s*([^|\n.;]{2,' + str(max_len) + r'})'
    m = re.search(pattern, text)
    return _clean(m.group(1)) if m else None


def _deadline(text):
    from intelligence.source_content import extract_deadline
    return extract_deadline(text)


def _funding(text):
    from intelligence.source_content import extract_funding
    return extract_funding(text)


def _tuition(text):
    from intelligence.source_content import extract_tuition
    return extract_tuition(text)


def extract_source_facts(text: str) -> dict:
    text = re.sub(r'\s+', ' ', str(text or ' ')).strip()
    return {
        'deadline': _deadline(text),
        'funding': _funding(text),
        'tuition': _tuition(text),
        'facts_checked_at': datetime.utcnow().isoformat() + 'Z',
        'facts_source': 'actual_source_page',
    }


def apply_source_facts(item):
    meta = dict(getattr(item, 'metadata', {}) or {})
    facts = meta.get('source_facts') or {}
    for field in ('deadline','funding','tuition'):
        value = facts.get(field)
        if value:
            setattr(item, field, value)
        elif not getattr(item, field, None) or str(getattr(item, field)).strip() in {'N/A','None'}:
            setattr(item, field, NA)
    meta['fact_display_rule'] = 'Only explicit source-page facts are displayed; unavailable values remain N/A.'
    item.metadata = meta
    return item
