"""LLM quality review for already-retrieved opportunity pages.

The LLM is used as a second-stage judge, not as the web search engine. Search first,
fetch the real page, then ask the model whether the page actually matches the user's
requested opportunity type/country/level and whether it is current/actionable.
"""
from __future__ import annotations

import asyncio
import json
import re
from datetime import date
from typing import Any

from config.settings import GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY
from llm.manager import LLMManager

BATCH_SIZE = 6
MAX_LLM_CANDIDATES = 180


def external_llm_available() -> bool:
    return bool(GEMINI_API_KEY or GROQ_API_KEY or OPENROUTER_API_KEY)


def _strip_json(raw: str) -> str:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.I)
        raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def _parse(raw: str) -> list[dict[str, Any]]:
    text = _strip_json(raw)
    try:
        data = json.loads(text)
    except Exception:
        start = text.find("[")
        end = text.rfind("]")
        if start < 0 or end <= start:
            return []
        try:
            data = json.loads(text[start:end + 1])
        except Exception:
            return []
    return data if isinstance(data, list) else []


def _grounded(value: str, page: str) -> bool:
    """True only if (almost) every meaningful word of an LLM-supplied value appears on the page."""
    words = [w for w in re.findall(r"[a-z0-9]+", (value or "").lower()) if len(w) > 2 or w.isdigit()]
    if not words:
        return False
    low = (page or "").lower()
    hits = sum(1 for w in words if w in low)
    digits = [w for w in words if w.isdigit()]
    return hits / len(words) >= 0.8 and all(d in low for d in digits)


def _candidate_payload(item: Any, index: int) -> dict[str, Any]:
    meta = getattr(item, "metadata", {}) or {}
    description = str(getattr(item, "description", "") or "")
    return {
        "id": index,
        "title": str(getattr(item, "title", "") or "")[:300],
        "organization": str(getattr(item, "organization", "") or "")[:200],
        "country": str(getattr(item, "country", "") or "")[:120],
        "url": str(getattr(item, "application_url", "") or getattr(item, "source_url", "") or ""),
        "source_tier": str(meta.get("source_tier", "") or ""),
        "page_text": description[:3200],
    }


async def _review_batch(manager: LLMManager, plan: Any, items: list[Any], offset: int) -> list[dict[str, Any]]:
    payload = [_candidate_payload(item, offset + i) for i, item in enumerate(items)]
    requested_type = plan.opportunity_type
    requested_level = plan.study_level if requested_type in {"Study / Degree", "Scholarship", "Master's"} else plan.research_level
    prompt = f"""
Review these retrieved opportunity SOURCE PAGES for a user request.

CURRENT DATE: {date.today().isoformat()}

USER REQUEST
- opportunity type: {requested_type}
- study/research level: {requested_level}
- countries: {', '.join(plan.countries) or 'any'}
- fields: {', '.join(plan.fields) or 'any'}
- extra terms: {', '.join(plan.roles) if requested_type in {'Job','Internship'} else 'none'}

IMPORTANT:
1. Judge ONLY the supplied page text and metadata. Do not invent missing facts.
2. A search result is not enough: the supplied URL must be the actual opportunity/source page.
3. Reject expired/closed opportunities, discussion/forum/community pages, news/blog/listicle/guide pages, and generic databases or programme catalogues when they are not themselves the requested opportunity.
4. For SCHOLARSHIP, reject a Master's/degree programme unless the page clearly offers a scholarship, fellowship, grant, stipend, tuition waiver, financial aid or other student funding mechanism and an actionable route. A scholarship mention inside a generic degree catalogue is not enough.
5. For JOB, require an actual vacancy/hiring/employment opportunity, not a career guide or company jobs homepage.
6. For INTERNSHIP, require an actual internship/placement/trainee opportunity.
7. For STUDY / DEGREE, require an actual degree/admissions opportunity at the requested level.
8. For RESEARCH, require an actual research position/programme/fellowship opportunity matching the requested level.
9. Country and level must match the user's request. Do not accept merely because the institution has an international website.
10. Compare every explicit deadline with CURRENT DATE. If the deadline is before CURRENT DATE, reject it as expired even if the page still exists.
11. Current means the page gives no evidence that applications are closed/expired. If dates are absent, do NOT invent a deadline; currentness may still be accepted only when the page has clear ongoing/open/actionable language.
12. Reject social-media posts, forum threads, discussion pages, scraped posts, news articles, blogs, listicles and generic guides as final sources. If they mention a genuine opportunity, prefer the linked official application/source page instead.
13. Prefer direct official/organization source pages. Do not reject a genuine opportunity merely because its domain is not .edu/.gov.
14. A job posting, internship, postdoc/PhD vacancy, course page, news page or generic information page is NOT a scholarship. A scholarship, degree page or research ad is NOT a job. Set type_match=false and accept=false for any page whose main purpose is a different opportunity type.
15. Do not reject an opportunity ONLY because no deadline is stated; reject it when the page shows it is closed, expired or filled, or when the type, level or country is wrong.
16. Copy deadline and funding only if the page text states them verbatim; otherwise write "Not stated".
17. Score relevance from 0-100. 90+ = strong direct match; 75-89 = useful direct match; below 75 must be rejected.

Return ONLY a JSON array. One object per candidate:
{{"id":0,"accept":true,"score":94,"type_match":true,"country_match":true,"level_match":true,"current":true,"actionable":true,"deadline":"Not stated","funding":"Not stated","reason":"short evidence-based reason"}}

CANDIDATES:
{json.dumps(payload, ensure_ascii=False)}
"""
    system = "You are a strict opportunity-quality reviewer. You are a verifier/reranker, not a creative assistant. Return valid JSON only."
    try:
        raw = await manager.generate_external(prompt, system)
        return _parse(raw)
    except Exception:
        return []


async def llm_review(plan: Any, items: list[Any]) -> list[Any]:
    """Review and rank a bounded verified-page pool with the configured LLM."""
    if not items or not external_llm_available():
        return items

    items = items[:MAX_LLM_CANDIDATES]
    manager = LLMManager()
    batches = [items[i:i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    semaphore = asyncio.Semaphore(4)

    async def run_batch(batch: list[Any], offset: int):
        async with semaphore:
            return await _review_batch(manager, plan, batch, offset)

    reviewed = await asyncio.gather(
        *(run_batch(batch, i * BATCH_SIZE) for i, batch in enumerate(batches)),
        return_exceptions=True,
    )

    decisions: dict[int, dict[str, Any]] = {}
    for result in reviewed:
        if isinstance(result, Exception):
            continue
        for decision in result:
            try:
                decisions[int(decision.get("id"))] = decision
            except Exception:
                continue

    accepted, unreviewed = [], []
    reviewed_count = 0
    for index, item in enumerate(items):
        decision = decisions.get(index)
        if not decision:
            # This batch failed. The item already passed every deterministic gate, so it stays,
            # but it is marked as not AI-reviewed and ranked below reviewed matches.
            meta = dict(getattr(item, "metadata", {}) or {})
            meta["llm_reviewed"] = False
            meta["llm_review_status"] = "unavailable"
            item.metadata = meta
            unreviewed.append(item)
            continue
        reviewed_count += 1
        # An explicit rejection is final: the reviewer saw the real page and said it is the wrong type,
        # level, country, or closed. Rejections are never put back.
        if not bool(decision.get("accept")) or not bool(decision.get("type_match", True)):
            continue
        if decision.get("current") is False:
            continue
        if int(decision.get("score", 0) or 0) < 75:
            continue
        meta = dict(getattr(item, "metadata", {}) or {})
        meta["llm_reviewed"] = True
        meta["llm_quality_score"] = int(decision.get("score", 0) or 0)
        meta["llm_review_reason"] = str(decision.get("reason", "") or "")[:500]
        meta["llm_type_match"] = bool(decision.get("type_match"))
        meta["llm_country_match"] = bool(decision.get("country_match"))
        meta["llm_level_match"] = bool(decision.get("level_match"))
        meta["llm_current"] = bool(decision.get("current"))
        meta["llm_actionable"] = bool(decision.get("actionable"))
        item.metadata = meta
        page = str(getattr(item, "description", "") or "")
        deadline = str(decision.get("deadline", "") or "").strip()
        funding = str(decision.get("funding", "") or "").strip()
        # LLM-supplied facts are only kept when the page really says them.
        if deadline and deadline.lower() not in {"n/a", "unknown", "null", "not stated"} and _grounded(deadline, page):
            item.deadline = deadline
        if funding and funding.lower() not in {"n/a", "unknown", "null", "not stated"} and _grounded(funding, page):
            item.funding = funding
        accepted.append(item)

    accepted.sort(
        key=lambda x: (
            -int((getattr(x, "metadata", {}) or {}).get("llm_quality_score", 0)),
            (getattr(x, "title", "") or "").casefold(),
        )
    )
    return accepted + unreviewed
