import asyncio
import time
from sources.base import BaseSource

class SourceManager:
    def __init__(self, sources: list[BaseSource] | None = None):
        self.sources=list(sources or [])
        self._stats: dict[str, dict] = {}
        # Always add the live agentic Google source unless the caller already supplied it.
        try:
            from sources.google_grounded import GoogleGroundedSource
            if not any(isinstance(s, GoogleGroundedSource) for s in self.sources):
                self.sources.append(GoogleGroundedSource())
        except Exception:
            pass

    def register(self, source: BaseSource) -> None:
        self.sources.append(source)

    @property
    def diagnostics(self) -> list[dict]:
        """Per-source totals for this manager: result count, elapsed seconds, queries run, last error."""
        return [dict(v) for v in self._stats.values()]

    def _record(self, source, results: int, elapsed: float, error: str = ""):
        name = getattr(source, "name", None) or type(source).__name__
        row = self._stats.setdefault(name, {"source": name, "results": 0, "elapsed": 0.0, "calls": 0, "error": ""})
        row["results"] += results
        row["elapsed"] = round(row["elapsed"] + elapsed, 2)
        row["calls"] += 1
        if error:
            row["error"] = error[:300]

    async def _run_source(self, source, query, opportunity_type=None, country=None):
        started = time.perf_counter()
        try:
            items = await source.search(query, opportunity_type, country)
            self._record(source, len(items or []), time.perf_counter() - started)
            return items
        except Exception as exc:
            # One failing source must never stop discovery; it is reported in diagnostics.
            self._record(source, 0, time.perf_counter() - started, f"{type(exc).__name__}: {exc}")
            return []

    async def search(self, query, opportunity_type=None, country=None):
        if not self.sources:
            return []
        batches=await asyncio.gather(*[
            self._run_source(s, query, opportunity_type, country) for s in self.sources
        ], return_exceptions=True)
        return [item for batch in batches if isinstance(batch,list) for item in batch]
