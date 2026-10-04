"""Curated opportunity-source registry for broad, country-aware discovery."""
from __future__ import annotations
import json
from pathlib import Path
from functools import lru_cache

_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "opportunity_sources.json"

@lru_cache(maxsize=1)
def load_registry() -> dict:
    try:
        return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"countries": {}, "global_sources": []}

def country_names() -> list[str]:
    return list(load_registry().get("countries", {}).keys())

def sources_for(country: str, opportunity_type: str | None = None) -> list[dict]:
    data = load_registry()
    items = list(data.get("countries", {}).get(country, []))
    items += list(data.get("global_sources", []))
    wanted = {"scholarship":"scholarship", "Master's":"study", "Study / Degree":"study", "Research":"research", "Job":"job", "Internship":"internship"}.get(opportunity_type or "")
    if not wanted:
        return items
    preferred = [x for x in items if wanted in x.get("best_for", [])]
    other = [x for x in items if x not in preferred]
    return preferred + other

def domains_for(country: str, opportunity_type: str | None = None, limit: int = 12) -> list[str]:
    seen=set(); out=[]
    for item in sources_for(country, opportunity_type):
        d=str(item.get("domain","")).strip().lower().replace("www.","")
        if d and d not in seen:
            seen.add(d); out.append(d)
        if len(out)>=limit:
            break
    return out

def source_info(domain: str) -> dict:
    d=(domain or "").lower().replace("www.","")
    for country_items in load_registry().get("countries", {}).values():
        for item in country_items:
            if item.get("domain","").lower().replace("www.","")==d:
                return item
    for item in load_registry().get("global_sources", []):
        if item.get("domain","").lower().replace("www.","")==d:
            return item
    return {}


def scholarship_library() -> list[dict]:
    try:
        from intelligence.scholarship_library import load_library
        return list(load_library().get("entries", []))
    except Exception:
        return []

def scholarship_library_for(country: str | None = None, level: str = "Any", fields: list[str] | None = None) -> list[dict]:
    try:
        from intelligence.scholarship_library import search_seeds
        return search_seeds([country] if country else [], level, fields)
    except Exception:
        return []
