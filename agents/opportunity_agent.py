from intelligence.deduplication import deduplicate_opportunities
from intelligence.normalization import normalize_results
from sources.manager import SourceManager

class OpportunityAgent:
    def __init__(self, manager: SourceManager):
        self.manager = manager

    async def run(self, query, opportunity_type=None, country=None):
        results = await self.manager.search(query, opportunity_type, country)
        results = normalize_results(results)
        return deduplicate_opportunities(results)
