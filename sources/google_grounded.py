from __future__ import annotations
from urllib.parse import urlparse
from datetime import date
from models.opportunity import Opportunity
from sources.base import BaseSource
from llm.manager import LLMManager

try:
    from intelligence.scholarship_websites import domain_hints
except Exception:
    domain_hints = lambda country=None, limit=12: []

class GoogleGroundedSource(BaseSource):
    """Agentic Google Search source.

    Gemini performs live Google Search, while Opportune supplies the opportunity-specific
    search agent instructions. Returned URLs are candidates only; the discovery planner
    fetches and verifies the actual pages before accepting them.
    """
    name="Google Search (Agentic Grounding)"

    def _prompt(self, query, opportunity_type, country):
        today=date.today().isoformat()
        hints=domain_hints(country, 14) if opportunity_type=="Scholarship" else []
        hint_text=", ".join(hints)
        rules={
            "Scholarship": "Find individual scholarships, fellowships, grants, stipends, tuition waivers or financial-aid programmes. Do not return articles, listicles, discussion posts, generic 'top scholarships' pages, job/internship pages, or ordinary degree programmes unless the page itself describes the funding opportunity.",
            "Master's": "Find actual Master's degree/admission opportunities. Prefer university programme/admission pages. Do not return scholarship-only pages, articles or rankings.",
            "Research": "Find actual research positions, funded PhD/research programmes, fellowships, labs recruiting researchers, or professor/lab opportunities. Prefer official university/lab pages.",
            "Internship": "Find actual internship/placement/trainee vacancies with an application route. Prefer employer career pages and reputable vacancy pages.",
            "Job": "Find actual open job vacancies with an application route. Prefer employer career pages and reputable job portals.",
        }.get(opportunity_type, "Find actual actionable opportunities.")
        return f"""
You are the {opportunity_type or 'Opportunity'} Discovery Agent inside Opportune AI.
Today: {today}
User search: {query}
Requested country: {country or 'ANY COUNTRY'}
{rules}

Search the live public web using Google Search. Use multiple search queries when useful.
Prioritize current 2026 opportunities and official/organization/university sources.
For scholarships, useful source domains include: {hint_text or 'official government, university and scholarship organizations'}.
The output is being used only to discover URLs; Opportune will fetch every page and verify it separately.
Do not invent URLs. Do not treat snippets as verified facts.
Return enough distinct source pages to give the verifier a useful pool (aim for 15-20).
"""

    async def search(self, query, opportunity_type=None, country=None):
        manager=LLMManager()
        if not manager.has_external_provider:
            return []
        rows=await manager.search_web(self._prompt(query,opportunity_type,country), max_results=20)
        out=[]; seen=set()
        for row in rows:
            url=str(row.get("url","")).strip()
            if not url or url in seen: continue
            host=urlparse(url).netloc.lower()
            if not host: continue
            seen.add(url)
            title=row.get("title") or host
            snippet=row.get("snippet") or ""
            out.append(Opportunity(
                title=title,
                organization=host.replace("www.",""),
                opportunity_type=(opportunity_type or "UNKNOWN").upper(),
                country=country or None,
                description=snippet[:3000],
                application_url=url,
                source_url=url,
                source_name=self.name,
                verification_status="UNVERIFIED",
                metadata={
                    "discovery_engine":"gemini_google_grounding" if any(getattr(p,"name","")=="gemini" for p in manager.providers) else "serper",
                    "grounded_search":True,
                    "search_snippet":snippet[:1500],
                    "destination_url":url,
                },
            ))
        return out
