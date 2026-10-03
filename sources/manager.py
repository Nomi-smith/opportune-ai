import asyncio
from sources.base import BaseSource

class SourceManager:
    def __init__(self, sources: list[BaseSource] | None = None):
        self.sources = sources or []
        self.diagnostics: list[dict] = []

    def register(self, source: BaseSource) -> None:
        self.sources.append(source)

    async def _run_source(
        self, source: BaseSource, query: str,
        opportunity_type: str | None = None, country: str | None = None
    ) -> list:
        try:
            items = await source.search(query, opportunity_type, country)
            error = getattr(source, "last_error", "")
            self.diagnostics.append({
                "source": getattr(source, "name", source.__class__.__name__),
                "query": query,
                "count": len(items or []),
                "error": error or "",
            })
            return items or []
        except Exception as exc:
            self.diagnostics.append({
                "source": getattr(source, "name", source.__class__.__name__),
                "query": query,
                "count": 0,
                "error": str(exc)[:500],
            })
            return []

    async def search(
        self, query: str, opportunity_type: str | None = None,
        country: str | None = None
    ) -> list:
        if not self.sources:
            return []
        results = await asyncio.gather(*[
            self._run_source(s, query, opportunity_type, country)
            for s in self.sources
        ])
        return [item for batch in results for item in batch]
