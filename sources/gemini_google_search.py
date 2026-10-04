import os
import httpx
from models.opportunity import Opportunity
from sources.base import BaseSource

class GeminiGoogleSearchSource(BaseSource):
    name = 'Google Search (Gemini Grounding)'
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY', '')
        self.model = os.getenv('GEMINI_SEARCH_MODEL', 'gemini-3.8-flash')
        self.timeout = float(os.getenv('GEMINI_SEARCH_TIMEOUT', '8'))

    async def search(self, query, opportunity_type=None, country=None):
        if not self.api_key: return []
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent'
        prompt = f'''Find current actionable {opportunity_type or "opportunities"} on the public web for: {query} {country or ""}.
Prefer official application pages. Ignore expired or historical opportunities. Return concise grounded results.'''
        payload = {'contents':[{'parts':[{'text':prompt}]}], 'tools':[{'google_search':{}}]}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(url, params={'key':self.api_key}, json=payload)
                r.raise_for_status(); data=r.json()
        except Exception:
            return []
        out=[]; seen=set()
        for chunk in (data.get('candidates') or [{}])[0].get('groundingMetadata',{}).get('groundingChunks',[]):
            web=chunk.get('web') or {}
            u=web.get('uri')
            if not u or u in seen: continue
            seen.add(u)
            out.append(Opportunity(id=f'gemini:{u}', title=web.get('title') or u, organization='', opportunity_type=(opportunity_type or 'UNKNOWN').upper(), country=country or None, description='', application_url=u, source_url=u, source_name=self.name, metadata={'search_provider':'gemini_grounding'}))
        return out[:6]
