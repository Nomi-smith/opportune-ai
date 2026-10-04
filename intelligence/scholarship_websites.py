"""Fast access to the curated scholarship/study source library."""
from __future__ import annotations
import csv
from pathlib import Path
from functools import lru_cache

CSV_PATH = Path(__file__).resolve().parents[1] / "config" / "scholarship_sources.csv"

@lru_cache(maxsize=1)
def load_sources() -> list[dict]:
    try:
        with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []

def _norm_country(value: str) -> str:
    return (value or "").strip().casefold()

def _host(url: str) -> str:
    from urllib.parse import urlparse
    return urlparse(url or "").netloc.lower().replace("www.", "")

def sources_for(country: str | None = None, limit: int = 20) -> list[dict]:
    rows = load_sources()
    country_key = _norm_country(country)
    selected = []
    if country_key:
        selected = [r for r in rows if _norm_country(r.get("Country / Region")) in {country_key, "global", "european union"}]
    else:
        selected = rows
    # Prefer actual scholarship/government/foundation sources over generic universities/aggregators.
    rank = {
        "Government": 0, "Government Portal": 0, "Government/Institutional": 0,
        "Government/Institution": 0, "Private Foundations": 1, "Private Foundation": 1,
        "Foundation / Trust": 1, "Private/Institutional": 1, "Private": 2,
        "Aggregator": 3, "University": 2, "Research Agency": 1,
        "International Organization": 1,
    }
    selected = sorted(selected, key=lambda r: (
        rank.get(r.get("Type",""), 4),
        0 if "scholar" in (r.get("Name","").lower()) else 1,
        r.get("Name","").casefold(),
    ))
    seen=set(); out=[]
    for r in selected:
        host=_host(r.get("Website",""))
        if not host or host in seen:
            continue
        seen.add(host)
        out.append(r)
        if len(out) >= limit:
            break
    return out

def domain_hints(country: str | None = None, limit: int = 12) -> list[str]:
    return [_host(r.get("Website","")) for r in sources_for(country, limit) if _host(r.get("Website",""))]
