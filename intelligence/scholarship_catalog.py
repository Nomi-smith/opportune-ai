"""Browsable scholarship catalogue: the 597-entry source registry plus the curated programme library.

These are *sources to check*, not verified live opportunities. Current deadlines come from the
verified search on the Scholarships page.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

_CONFIG = Path(__file__).resolve().parents[1] / "config"


def _read(name: str) -> dict:
    try:
        return json.loads((_CONFIG / name).read_text(encoding="utf-8"))
    except Exception:
        return {}


def _key(url: str, name: str) -> str:
    u = urlparse(url or "")
    host = u.netloc.lower().replace("www.", "")
    return f"{host}{u.path.rstrip('/')}" if host else (name or "").casefold()


def _levels(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value or "")


@lru_cache(maxsize=1)
def load_catalog() -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()

    # Curated programmes first: they carry funding / typical-deadline notes.
    for item in _read("scholarship_library.json").get("entries", []):
        url = item.get("url") or item.get("source_url") or ""
        k = _key(url, item.get("name", ""))
        if k in seen:
            continue
        seen.add(k)
        kind = item.get("source_kind", "")
        rows.append({
            "name": item.get("name", ""), "country": item.get("country") or "Global",
            "category": "Catalogue / database" if kind == "catalogue" else "Featured programme",
            "level": _levels(item.get("level")), "funding": item.get("funding", ""),
            "open_to": "", "note": item.get("note", ""), "website": url,
        })

    for item in _read("scholarship_sources.json").get("entries", []):
        url = item.get("website", "")
        k = _key(url, item.get("name", ""))
        if k in seen:
            continue
        seen.add(k)
        rows.append({
            "name": item.get("name", ""), "country": item.get("country") or "Global",
            "category": item.get("type") or "Other", "level": _levels(item.get("level")),
            "funding": item.get("funding_model", ""), "open_to": item.get("open_to", ""),
            "note": "", "website": url,
        })
    rows.sort(key=lambda r: (r["country"] != "Global", r["country"], r["name"].casefold()))
    return rows


def catalog_options(rows: list[dict] | None = None) -> dict:
    rows = rows if rows is not None else load_catalog()
    return {
        "countries": sorted({r["country"] for r in rows}, key=lambda c: (c != "Global", c)),
        "categories": sorted({r["category"] for r in rows}),
    }


def _level_matches(row_level: str, wanted: str) -> bool:
    if not wanted or wanted == "Any":
        return True
    rl = row_level.casefold().replace("\u2019", "'")
    w = wanted.casefold().replace("\u2019", "'")
    w = w[:-2] if w.endswith("'s") else w
    return not rl or "all levels" in rl or w in rl


def filter_catalog(rows: list[dict], query: str = "", countries: list[str] | None = None,
                   categories: list[str] | None = None, level: str = "Any") -> list[dict]:
    q = (query or "").casefold().strip()
    out = []
    for r in rows:
        if countries and r["country"] not in countries:
            continue
        if categories and r["category"] not in categories:
            continue
        if not _level_matches(r["level"], level):
            continue
        if q and q not in " ".join((r["name"], r["country"], r["category"], r["note"], r["open_to"])).casefold():
            continue
        out.append(r)
    return out
