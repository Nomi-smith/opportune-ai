"""Natural-language agent routing for opportunity discovery.

The chat agent turns free-form user requests into the same structured search plan used by
Discover. It never fabricates opportunity facts; it only extracts intent and constraints.
"""
from __future__ import annotations

import json
import re
from typing import Any

from intelligence.discovery_planner import (
    COUNTRY_OPTIONS,
    FIELD_OPTIONS,
    ROLE_OPTIONS,
    STUDY_LEVELS,
    RESEARCH_LEVELS,
)
from llm.manager import LLMManager

TYPE_ALIASES = {
    "scholarship": "Scholarship", "scholarships": "Scholarship", "scholorship": "Scholarship", "scholorships": "Scholarship", "funding": "Scholarship",
    "financial aid": "Scholarship", "fellowship": "Scholarship", "grant": "Scholarship",
    "job": "Job", "jobs": "Job", "work": "Job", "employment": "Job",
    "internship": "Internship", "internships": "Internship", "trainee": "Internship",
    "master": "Master's", "masters": "Master's", "master's": "Master's", "ms": "Master's",
    "degree": "Master's", "study": "Master's", "admission": "Master's", "admissions": "Master's",
    "research": "Research", "phd": "Research", "doctoral": "Research", "postdoc": "Research",
}


def _clean(values):
    out, seen = [], set()
    for value in values or []:
        value = str(value or "").strip()
        if value and value.casefold() not in seen:
            seen.add(value.casefold()); out.append(value)
    return out


def _normalise_type(value: str) -> str:
    low = str(value or "").strip().casefold()
    if low in TYPE_ALIASES:
        return TYPE_ALIASES[low]
    for alias, canonical in TYPE_ALIASES.items():
        if alias in low:
            return canonical
    return "All"


def _match_options(text: str, options: list[str], limit=5):
    low = text.casefold()
    found=[]
    for option in options:
        if option.casefold() in low:
            found.append(option)
    return found[:limit]


def _fallback_intent(text: str, previous: dict | None = None) -> dict[str, Any]:
    previous = previous or {}
    low = text.casefold()
    opportunity_type = _normalise_type(low)
    if opportunity_type == "All":
        opportunity_type = previous.get("opportunity_type", "All") or "All"

    countries = _match_options(text, COUNTRY_OPTIONS, 8) or _clean(previous.get("countries", []))
    fields = _match_options(text, FIELD_OPTIONS, 8) or _clean(previous.get("fields", []))
    roles = _match_options(text, ROLE_OPTIONS, 8) or _clean(previous.get("roles", []))

    # Common aliases not represented exactly in the UI labels.
    aliases = {
        "china": "China", "germany": "Germany", "sweden": "Sweden", "japan": "Japan",
        "usa": "United States", "us": "United States", "uk": "United Kingdom",
        "korea": "South Korea", "uae": "United Arab Emirates",
        "ai": "Artificial Intelligence", "artificial intelligence": "Artificial Intelligence",
        "ml": "Machine Learning", "machine learning": "Machine Learning",
        "cs": "Computer Science", "computer science": "Computer Science",
    }
    for needle, canonical in aliases.items():
        if re.search(r"\b" + re.escape(needle) + r"\b", low) and canonical not in countries + fields:
            (countries if canonical in COUNTRY_OPTIONS else fields).append(canonical)

    level = previous.get("study_level", "Any") or "Any"
    for candidate in STUDY_LEVELS:
        if candidate != "Any" and candidate.casefold() in low:
            level = candidate
    research_level = previous.get("research_level", "Any") or "Any"
    for candidate in RESEARCH_LEVELS:
        if candidate != "Any" and candidate.casefold() in low:
            research_level = candidate

    return {
        "intent": "discover" if opportunity_type != "All" or countries or fields or roles else "chat",
        "opportunity_type": opportunity_type,
        "roles": _clean(roles),
        "countries": _clean(countries),
        "fields": _clean(fields),
        "study_level": level,
        "research_level": research_level,
        "extra_terms": text,
        "confidence": 0.55,
    }


async def understand(text: str, previous: dict | None = None) -> dict[str, Any]:
    """Parse a natural-language request into a safe structured intent."""
    previous = previous or {}
    manager = LLMManager()
    if not manager.has_external_provider:
        return _fallback_intent(text, previous)

    prompt = f"""
Convert the user's natural-language message into a structured Opportune AI request.
This is intent extraction only. Never invent facts or opportunities.

CURRENT CONVERSATION CONTEXT:
{json.dumps(previous, ensure_ascii=False)}

USER MESSAGE:
{text}

Allowed opportunity_type values: All, Job, Internship, Master's, Scholarship, Research.
Allowed study_level values: Any, Bachelor's, Master's, PhD.
Allowed research_level values: Any, PhD, Postdoc, Research Assistant.
Known countries: {', '.join(COUNTRY_OPTIONS)}
Known fields: {', '.join(FIELD_OPTIONS)}
Known roles: {', '.join(ROLE_OPTIONS)}

Rules:
- Resolve follow-ups using the context. If the user says "China" after asking for Germany, change only country.
- "scholarship", "funding", "financial aid", "fellowship" => Scholarship.
- "internship" => Internship; "job/work/vacancy" => Job.
- "master's/MS/masters admission" => Master's.
- "research/PhD/doctoral/postdoc" => Research.
- Extract countries, fields, roles and level only when stated or clearly expressed.
- Preserve custom field terms in extra_terms.
- If this is casual conversation rather than a search, use intent="chat".

Return ONLY JSON:
{{
  "intent":"discover|chat|clarify",
  "opportunity_type":"All|Job|Internship|Master's|Scholarship|Research",
  "roles":[], "countries":[], "fields":[],
  "study_level":"Any|Bachelor's|Master's|PhD",
  "research_level":"Any|PhD|Postdoc|Research Assistant",
  "extra_terms":"",
  "confidence":0.0
}}
"""
    try:
        raw = await manager.generate_external(prompt, "You are a strict intent parser. Return JSON only.")
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start:end + 1])
            if isinstance(data, dict):
                fallback = _fallback_intent(text, previous)
                for key in fallback:
                    if key not in data or data[key] in (None, "", []):
                        data[key] = fallback[key]
                data["opportunity_type"] = _normalise_type(data.get("opportunity_type", "All"))
                data["roles"] = _clean(data.get("roles", []))
                data["countries"] = _clean(data.get("countries", []))
                data["fields"] = _clean(data.get("fields", []))
                return data
    except Exception:
        pass
    return _fallback_intent(text, previous)
