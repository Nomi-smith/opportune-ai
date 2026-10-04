"""Turn a fetched opportunity page into clean, structured facts for the document builder.

Two layers:
1. Rules (always on): strip page chrome, pick the real heading, find deadline / amount / organisation.
2. LLM (only if a provider is configured): reads the cleaned page and returns structured fields.
   Every LLM field is grounded: a deadline, amount or name that does not appear in the page text is dropped,
   so a model can tidy and summarise the page but never invent facts.
"""
from __future__ import annotations

import json
import re
from urllib.parse import urlparse

KINDS = ("Job", "Internship", "Scholarship", "Admission", "Research", "Other")

# Page-chrome phrases that survive HTML cleaning (skip links, login prompts, social widgets, cookie banners).
_CHROME = [
    r"\[?\s*skip to (?:main )?content\s*\]?", r"\[?\s*skip to (?:main )?navigation\s*\]?",
    r"login (?:to|with)\s+[A-Za-z ]{0,40}?(?=\s{2,}|[.!]|$)",
    r"log ?in(?: or| /)? (?:sign ?up|register|create (?:an )?account)",
    r"follow us(?: on)?(?: facebook| twitter| linkedin| instagram| x| youtube)*",
    r"we use cookies[^.]*\.", r"accept (?:all )?cookies", r"cookie (?:settings|policy|preferences)",
    r"share (?:this )?(?:on|via) (?:facebook|twitter|linkedin|email|whatsapp)",
    r"(?:facebook|twitter|linkedin|instagram|youtube)\s+(?=(?:facebook|twitter|linkedin|instagram|youtube))",
    r"\bprivacy policy\b", r"\bterms (?:of use|and conditions)\b", r"all rights reserved\.?",
    r"copyright\s*©?\s*\d{4}[^.]{0,60}", r"\bback to top\b", r"\bsubscribe to (?:our )?newsletter\b",
]
_CHROME_RE = re.compile("|".join(_CHROME), re.I)

_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
_DATE = rf"(?:\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}\.?,?\s+\d{{4}}|{_MONTH}\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}|\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}[/.]\d{{1,2}}[/.]\d{{4}})"
_DEADLINE_RES = [
    re.compile(rf"(?:applications?|submissions?|apply)\s*(?:are\s*)?(?:due|deadline|close[sd]?|by)\s*(?:on|:|-)?\s*[^.\n]{{0,40}}?({_DATE})", re.I),
    re.compile(rf"(?:deadline|closing date|closes?|last day to apply|apply by|due date)\s*(?:is|on|:|-)?\s*[^.\n]{{0,40}}?({_DATE})", re.I),
]
_AMOUNT_RE = re.compile(
    r"((?:US\$|USD|EUR|GBP|CAD|AUD|CHF|SEK|NOK|DKK|€|£|\$)\s?\d[\d,.]*(?:\s?(?:k|K|million|per (?:month|year|annum)|/(?:month|year)))?"
    r"(?:\s*(?:to|-|–)\s*(?:US\$|USD|EUR|GBP|€|£|\$)?\s?\d[\d,.]*)?)")
_ORG_PATTERNS = [
    re.compile(r"(?:sponsored|offered|funded|awarded|provided|hosted|organi[sz]ed) by\s+(?:the\s+)?([A-Z][\w&.\-]*(?:\s+[A-Z&][\w&.\-]*){0,5})"),
    re.compile(r"(?:about|join|work(?:ing)? (?:at|for))\s+([A-Z][\w&.\-]*(?:\s+[A-Z&][\w&.\-]*){0,4})(?=[.,:\n]|\s+is\b|\s+we\b)"),
]
_GENERIC_ORG = re.compile(r"^(?:about|home|welcome|careers?|jobs?|apply|scholarships?|login|page)\b", re.I)


# ----------------------------------------------------------------- cleaning
def clean_page_text(text: str, max_chars: int = 9000) -> str:
    """Remove page chrome and collapse whitespace. Keeps the real content order."""
    text = _CHROME_RE.sub(" ", text or "")
    text = re.sub(r"\[\s*\]", " ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text[:max_chars]


def content_text(page: dict, max_chars: int = 9000) -> str:
    """Cleaned page text that starts at the page's own heading (drops login/menu text before it)."""
    raw = page.get("text") or ""
    h1 = (page.get("h1") or "").strip()
    if h1:
        idx = raw.find(h1)
        if 0 < idx < 2500:
            raw = raw[idx:]
    return clean_page_text(raw, max_chars)


def _domain_name(url: str) -> str:
    host = urlparse(url or "").netloc.lower().replace("www.", "")
    if not host:
        return ""
    parts = host.split(".")
    # secure-platform.com / lever.co style hosts are platforms, not the organisation
    platforms = {"secure-platform", "lever", "greenhouse", "workable", "smartrecruiters", "myworkdayjobs", "bamboohr", "ashbyhq", "jobs"}
    candidates = [p for p in parts[:-1] if p not in platforms and p not in {"com", "org", "net", "co", "gov", "edu", "ac"}]
    name = (candidates[-1] if candidates else parts[0]).replace("-", " ")
    return name.upper() if len(name) <= 5 else name.title()


# ----------------------------------------------------------------- rules
def _guess_kind(title: str, text: str) -> str:
    blob = f"{title} {text[:1500]}".casefold()
    scores = {
        "Internship": len(re.findall(r"\binterns?(?:hip)?s?\b|\btrainee", blob)),
        "Scholarship": len(re.findall(r"scholarship|fellowship|bursary|stipend|tuition waiver|financial aid|\bgrant\b", blob)),
        "Research": len(re.findall(r"phd position|doctoral|postdoc|research (?:position|assistant|fellow)", blob)),
        "Admission": len(re.findall(r"admission|degree programme|degree program|master'?s programme|master'?s program|apply for (?:the )?(?:master|bachelor)", blob)),
        "Job": len(re.findall(r"responsibilit|qualifications|job description|we are hiring|full[- ]time|part[- ]time|years of experience|salary", blob)),
    }
    kind, score = max(scores.items(), key=lambda kv: kv[1])
    return kind if score > 0 else "Other"


def _pick_title(page: dict) -> str:
    h1 = (page.get("h1") or "").strip()
    title = (page.get("title") or "").strip()
    site = (page.get("site") or "").strip()
    # A generic site/page title ("About X Scholarships", "Careers") is worse than the page heading.
    if h1 and 8 <= len(h1) <= 200:
        return h1
    if title and not _GENERIC_ORG.match(title):
        return title
    return title or h1


def _pick_org(page: dict, text: str, url: str) -> str:
    site = (page.get("site") or "").strip()
    if site and not _GENERIC_ORG.match(site) and len(site) <= 60:
        return site
    parts = re.split(r"\s+[|\u2013\u2014-]\s+", page.get("title") or "")
    if len(parts) > 1:
        heading = _norm(page.get("h1") or "")
        for part in reversed(parts):
            part = part.strip()
            if 2 <= len(part) <= 40 and not _GENERIC_ORG.match(part) and _norm(part) != heading \
                    and _norm(part) not in _norm(_pick_title(page)):
                return part
    domain = _domain_name(url)
    if domain:
        return domain
    m = _ORG_PATTERNS[0].search(text[:3000])
    return m.group(1).strip(" .,-") if m else ""


def rule_extract(page: dict, url: str = "") -> dict:
    text = content_text(page)
    deadline = ""
    for rx in _DEADLINE_RES:
        m = rx.search(text)
        if m:
            deadline = m.group(1).strip()
            break
    amounts = []
    for m in _AMOUNT_RE.finditer(text):
        val = re.sub(r"\s+", " ", m.group(1)).strip(" .,")
        if re.search(r"\d{2,}", val) and val not in amounts:
            amounts.append(val)
        if len(amounts) >= 3:
            break
    title = _pick_title(page)
    return {
        "title": title,
        "organization": _pick_org(page, text, url),
        "kind": _guess_kind(title, text),
        "location": "",
        "deadline": deadline,
        "funding": "; ".join(amounts),
        "eligibility": [],
        "requirements": [],
        "how_to_apply": "",
        "summary": "",
        "description": text[:3500],
        "used_llm": False,
    }


# ----------------------------------------------------------------- LLM
LLM_SYSTEM = ("You extract facts from one opportunity web page (job, internship, scholarship, admission or research position). "
              "Use ONLY text present in the page. Never invent or guess. Use empty strings or empty lists when the page does not say. "
              "Return valid JSON only.")


def _llm_prompt(text: str, title_hint: str, url: str) -> str:
    return f"""Extract the opportunity described on this page.
Return JSON with exactly these keys:
title (the specific opportunity name, not the website name), organization (who offers/employs/funds it),
kind (one of: Job, Internship, Scholarship, Admission, Research, Other), location, deadline (as written on the page),
funding (salary, award amount or funding as written), eligibility (list of short items), requirements (list of short items:
documents, skills, qualifications), how_to_apply (one or two sentences), summary (max 60 words),
description (the relevant content only: no menus, logins, social links or footers; max 1800 characters).

URL: {url}
Page heading hint: {title_hint}

PAGE TEXT:
{text[:9000]}
"""


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").casefold()).strip()


def _in_page(value: str, page_norm: str, page_digits: str) -> bool:
    """A claim is grounded when its words (or its digits, for dates/amounts) occur in the page."""
    value = str(value or "").strip()
    if not value:
        return False
    digits = re.sub(r"\D", "", value)
    if digits and len(digits) >= 3:
        return digits in page_digits or _norm(value) in page_norm
    tokens = [t for t in _norm(value).split() if len(t) > 2]
    if not tokens:
        return False
    hit = sum(1 for t in tokens if t in page_norm)
    return hit / len(tokens) >= 0.6


def _as_list(value) -> list[str]:
    if isinstance(value, str):
        value = [v for v in re.split(r"[\n;•]+", value)]
    out = []
    for item in value or []:
        item = re.sub(r"\s+", " ", str(item)).strip(" -•\t")
        if item and item.casefold() not in {x.casefold() for x in out}:
            out.append(item[:240])
    return out[:10]


def merge_llm(base: dict, data: dict, page_text: str, url: str = "") -> dict:
    """Overlay grounded LLM fields on the rule-based result."""
    page_norm = _norm(page_text)
    page_digits = re.sub(r"\D", "", page_text)
    out = dict(base)
    title = str(data.get("title") or "").strip()
    if title and _in_page(title, page_norm, ""):
        out["title"] = title[:200]
    org = str(data.get("organization") or "").strip()
    org_tokens = [t for t in _norm(org).split() if len(t) > 2]
    org_hit = sum(1 for t in org_tokens if t in page_norm or t in _norm(url))
    if org and org_tokens and org_hit / len(org_tokens) >= 0.5:
        out["organization"] = org[:80]
    kind = str(data.get("kind") or "").strip().title()
    if kind in KINDS:
        out["kind"] = kind
    for key in ("location", "deadline", "funding"):
        val = str(data.get(key) or "").strip()
        if val and _in_page(val, page_norm, page_digits):
            out[key] = val[:200]
    for key in ("eligibility", "requirements"):
        items = [x for x in _as_list(data.get(key)) if _in_page(x, page_norm, page_digits)]
        if items:
            out[key] = items
    how = str(data.get("how_to_apply") or "").strip()
    if how and _in_page(how, page_norm, page_digits):
        out["how_to_apply"] = how[:400]
    summary = str(data.get("summary") or "").strip()
    if summary:
        out["summary"] = summary[:500]
    desc = clean_page_text(str(data.get("description") or ""), 2200)
    if len(desc) >= 120 and _in_page(desc[:400], page_norm, ""):
        out["description"] = desc
    out["used_llm"] = True
    return out


def parse_llm_json(raw: str) -> dict:
    start, end = (raw or "").find("{"), (raw or "").rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(raw[start:end + 1])
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


async def extract_opportunity(page: dict, url: str = "", manager=None) -> dict:
    """Rule extraction, improved by the LLM when one is configured. Never raises."""
    base = rule_extract(page, url)
    if manager is None or not getattr(manager, "has_external_provider", False):
        return base
    text = content_text(page)
    if len(text) < 200:
        return base
    try:
        raw = await manager.generate_external(_llm_prompt(text, base["title"], url), LLM_SYSTEM)
        data = parse_llm_json(raw)
        return merge_llm(base, data, text, url) if data else base
    except Exception:
        return base


# ----------------------------------------------------------------- output
def details_block(info: dict, url: str = "") -> str:
    """Readable structured text for the 'Opportunity details' box and for letter prompts."""
    lines = []
    if info.get("kind") and info["kind"] != "Other":
        lines.append(f"Type: {info['kind']}")
    for label, key in (("Location", "location"), ("Deadline", "deadline"), ("Funding / pay", "funding")):
        if info.get(key):
            lines.append(f"{label}: {info[key]}")
    if info.get("summary"):
        lines += ["", "Summary:", info["summary"]]
    for label, key in (("Eligibility", "eligibility"), ("Requirements", "requirements")):
        if info.get(key):
            lines += ["", f"{label}:"] + [f"- {x}" for x in info[key]]
    if info.get("how_to_apply"):
        lines += ["", "How to apply:", info["how_to_apply"]]
    if info.get("description"):
        lines += ["", "Page content:", info["description"]]
    if url:
        lines += ["", f"Source: {url}"]
    return "\n".join(lines).strip()
