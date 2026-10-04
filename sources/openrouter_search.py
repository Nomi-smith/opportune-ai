import os, re
import httpx
from models.opportunity import Opportunity
from sources.base import BaseSource

class OpenRouterWebSearchSource(BaseSource):
    name = 'OpenRouter Web Search'

    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY', '')
        self.model = os.getenv('OPENROUTER_SEARCH_MODEL', 'openrouter/free')
        self.engine = os.getenv('OPENROUTER_SEARCH_ENGINE', 'auto')
        self.timeout = float(os.getenv('SEARCH_PROVIDER_TIMEOUT', '8'))

    async def search(self, query, opportunity_type=None, country=None):
        if not self.api_key:
            return []
        prompt = f'''Search the live web for CURRENT, ACTIONABLE {opportunity_type or "opportunities"} matching this query: {query} {country or ""}.
Return only a compact list of results with title, organization if visible, URL, and a one-sentence snippet. Prefer official opportunity pages and current application pages. Exclude expired/historical pages.'''
        payload = {
            'model': self.model,
            'messages': [{'role': 'user', 'content': prompt}],
            'tools': [{'type': 'openrouter:web_search', 'parameters': {
                'engine': self.engine, 'max_results': 6, 'max_total_results': 6,
                'search_context_size': 'low'
            }}],
        }
        headers = {'Authorization': f'Bearer {self.api_key}', 'Content-Type': 'application/json', 'HTTP-Referer': 'https://opportune-ai.local', 'X-Title': 'Opportune AI'}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                r = await client.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload)
                r.raise_for_status(); data = r.json()
        except Exception:
            return []
        message = (data.get('choices') or [{}])[0].get('message') or {}
        content = message.get('content') or ''
        annotations = message.get('annotations') or []
        rows = []
        for a in annotations:
            c = a.get('url_citation') if isinstance(a, dict) else None
            if c and c.get('url'):
                rows.append((c.get('title') or c.get('url'), c.get('url'), c.get('content') or ''))
        if not rows:
            for m in re.finditer(r'(https?://[^\s)<>]+)', content):
                url = m.group(1).rstrip('.,')
                rows.append((url, url, content[:500]))
        out, seen = [], set()
        for title, url, snippet in rows:
            if url in seen or not url.startswith('http'): continue
            seen.add(url)
            out.append(Opportunity(
                id=f'openrouter:{url}', title=title, organization='',
                opportunity_type=(opportunity_type or 'UNKNOWN').upper(), country=country or None,
                description=snippet, application_url=url, source_url=url,
                source_name=self.name, metadata={'search_snippet': snippet, 'search_provider': 'openrouter'}
            ))
        return out[:6]
