import os
import asyncio
import httpx
from models.opportunity import Opportunity
from sources.base import BaseSource

class SerperGoogleSource(BaseSource):
    name = 'Google Search (Serper)'

    def __init__(self):
        self.api_key = os.getenv('SERPER_API_KEY', '')
        self.timeout = float(os.getenv('SEARCH_PROVIDER_TIMEOUT', '8'))

    async def search(self, query, opportunity_type=None, country=None):
        if not self.api_key:
            return []
        q = f'{query} {country or ""}'.strip()
        payload = {'q': q, 'num': 8}
        headers = {'X-API-KEY': self.api_key, 'Content-Type': 'application/json'}
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                r = await client.post('https://google.serper.dev/search', headers=headers, json=payload)
                r.raise_for_status()
                data = r.json()
        except Exception:
            return []
        out = []
        for item in data.get('organic', [])[:8]:
            url = item.get('link') or ''
            if not url.startswith('http'):
                continue
            title = item.get('title') or url
            snippet = item.get('snippet') or ''
            out.append(Opportunity(
                id=f'serper:{url}', title=title, organization='',
                opportunity_type=(opportunity_type or 'UNKNOWN').upper(),
                country=country or None, description=snippet,
                application_url=url, source_url=url, source_name=self.name,
                metadata={'search_snippet': snippet, 'search_provider': 'serper'}
            ))
        return out
