import asyncio

from sources.base import BaseSource


class SourceManager:
    def __init__(self, sources: list[BaseSource] | None = None):
        self.sources = sources or []

    def register(self, source: BaseSource) -> None:
        self.sources.append(source)

    async def _run_source(
        self,
        source: BaseSource,
        query: str,
        opportunity_type: str | None = None,
        country: str | None = None,
    ) -> list:
        try:
            return await source.search(
                query=query,
                opportunity_type=opportunity_type,
                country=country,
            )
        except Exception:
            return []

    async def search(
        self,
        query: str,
        opportunity_type: str | None = None,
        country: str | None = None,
    ) -> list:
        if not self.sources:
            return []

        tasks = [
            self._run_source(
                source,
                query,
                opportunity_type,
                country,
            )
            for source in self.sources
        ]

        results = await asyncio.gather(*tasks)

        opportunities = []

        for source_results in results:
            opportunities.extend(source_results)

        return opportunities