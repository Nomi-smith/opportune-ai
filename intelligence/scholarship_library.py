"""Seed library for scholarship discovery.

The library improves recall by giving Opportune AI known legitimate scholarship
programs/catalogues to search first. It is NOT treated as a live database:
current/expired status is determined from the fetched source page at runtime.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "config" / "scholarship_library.json"

def _norm_level(value) -> str:
    """'Master's' (UI) and 'Master' (library) are the same level."""
    v = str(value or "").casefold().replace("\u2019", "'").strip()
    return v[:-2] if v.endswith("'s") else v


@lru_cache(maxsize=1)
def load_library() -> dict:
    try:
        return json.loads(_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"entries": []}

def scholarship_entries(country: str | None = None, level: str = "Any", field: str | None = None) -> list[dict]:
    entries = list(load_library().get("entries", []))
    country = (country or "").strip().casefold()
    field = (field or "").strip().casefold()
    out = []
    for item in entries:
        if country and item.get("country", "").casefold() not in {country, "european union", "global", "worldwide"}:
            continue
        levels = {_norm_level(x) for x in item.get("level", [])}
        if level and level != "Any" and _norm_level(level) not in levels:
            continue
        if field:
            fields = " ".join(map(str, item.get("fields", []))).casefold()
            name = str(item.get("name", "")).casefold()
            if field not in fields and field not in name and "all fields" not in fields:
                continue
        out.append(item)
    return out

def search_seeds(countries: list[str], level: str = "Any", fields: list[str] | None = None) -> list[dict]:
    fields = fields or []
    out=[]; seen=set()
    target = [c for c in countries if c] or [None]
    for country in target:
        for field in fields[:3] or [None]:
            for item in scholarship_entries(country, level, field):
                key=item.get("name", "").casefold()
                if key not in seen:
                    seen.add(key); out.append(item)
        for item in scholarship_entries(country, level, None):
            key=item.get("name", "").casefold()
            if key not in seen:
                seen.add(key); out.append(item)
    return out

def seed_queries(countries: list[str], level: str = "Any", fields: list[str] | None = None, limit: int = 24) -> list[tuple[str, str, dict]]:
    rows=[]
    for item in search_seeds(countries, level, fields):
        country=item.get("country", "")
        aliases=item.get("search_aliases") or [item.get("name", "")]
        from urllib.parse import urlparse
        domain=urlparse(item.get("source_url", "")).netloc.replace("www.", "")
        for alias in aliases[:2]:
            q=f'"{alias}" scholarship'
            if level and level != "Any":
                q=f'{q} {level}'
            if fields:
                q=f'{q} {" ".join(fields[:2])}'
            if domain:
                q=f'{q} site:{domain}'
            rows.append((q, country, item))
    return rows[:limit]
