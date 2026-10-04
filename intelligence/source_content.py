"""Lightweight HTML content extraction and field extraction (grounded in the page text)."""
from __future__ import annotations

import re
from datetime import date

from bs4 import BeautifulSoup

REMOVE = ("script", "style", "noscript", "svg", "nav", "footer", "header", "aside", "form", "button",
          "iframe", "template", "dialog")
_CHROME_ATTR = re.compile(
    r"(?:^|[\s_-])(menu|navbar|nav|breadcrumbs?|cookie|consent|gdpr|skip|sidebar|topbar|footer|masthead|"
    r"social|share|newsletter|subscribe|banner|modal|popup|search-form|language|lang-switch)(?:$|[\s_-])", re.I)
_NOISE_LINE = re.compile(r"^(skip to (?:main )?content|menu|search|login|log in|sign in|register|share|follow us|"
                         r"cookies?|accept all|home|back to top|read more|print)\b", re.I)


def clean_source_html(html: str, max_chars: int = 30000) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(REMOVE):
        tag.decompose()
    # Menus, cookie bars and share widgets are usually <div class="...menu...">, not <nav>.
    for tag in soup.find_all(attrs={"class": _CHROME_ATTR}):
        tag.decompose()
    for tag in soup.find_all(attrs={"id": _CHROME_ATTR}):
        tag.decompose()
    for tag in soup.find_all(attrs={"role": re.compile(r"navigation|banner|contentinfo|search", re.I)}):
        tag.decompose()
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.find("article") or soup.find("body") or soup
    text = main.get_text("\n", strip=True)
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()]
    kept = [x for x in lines if x and not _NOISE_LINE.match(x)]
    return re.sub(r"\s+", " ", " ".join(kept)).strip()[:max_chars]


# ---------------------------------------------------------------- deadline
_MONTHS = ("january|february|march|april|may|june|july|august|september|october|november|december|"
           "jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec")
_DATE_TOKEN = re.compile(
    r"(?:\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:" + _MONTHS + r")\.?(?:,?\s+20\d{2})?\b)|"
    r"(?:\b(?:" + _MONTHS + r")\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+20\d{2})?\b)|"
    r"(?:\b20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\b)|(?:\b\d{1,2}[/.]\d{1,2}[/.]20\d{2}\b)", re.I)
_DEADLINE_MARK = re.compile(
    r"(?:application|applications|submission|apply|registration|nomination)?\s*"
    r"(?:deadline|deadlines|closes?|closing date|closing|due(?: date)?|last day to apply|apply by|apply before|"
    r"submit(?:ted)? by|must be received by)\b", re.I)
_ROLLING = re.compile(r"\b(rolling (?:basis|admissions?|applications?)|open until filled|applications? (?:are )?accepted year[- ]round|"
                      r"apply at any time|ongoing applications?)\b", re.I)


def _date_objs(text: str):
    from intelligence.freshness import _dates
    return _dates(text)


def extract_deadline(text: str) -> str | None:
    """Return a real date (or rolling-status phrase) found right after a deadline marker, else None.

    The value is always the date text itself, never a sentence fragment, so unrelated words
    that follow the word "deadline" can't leak into the Deadline field.
    """
    if not text:
        return None
    flat = re.sub(r"\s+", " ", text)
    found: list[str] = []
    for m in _DEADLINE_MARK.finditer(flat):
        window = flat[m.end(): m.end() + 140]
        tokens = [t.group(0).strip(" ,.") for t in _DATE_TOKEN.finditer(window)]
        if tokens:
            # keep at most the first two dates of a window ("25 April and 25 October")
            found.append(" / ".join(dict.fromkeys(tokens[:2])))
    if found:
        today = date.today()
        dated = [(min(d for d in _date_objs(f)), f) for f in found if _date_objs(f)]
        future = [x for x in dated if x[0] >= today]
        if future:
            return min(future)[1][:80]
        if dated:
            return max(dated)[1][:80]     # all in the past -> shown as passed and rejected upstream
        return found[0][:80]
    rolling = _ROLLING.search(flat)
    return rolling.group(1).capitalize() if rolling else None


# ---------------------------------------------------------------- funding
_MONEY = (r"(?:(?:US\$|USD|EUR|GBP|CNY|RMB|KRW|JPY|AUD|CAD|CHF|SEK|NOK|DKK|AED|SAR|PKR|INR|€|\$|£|¥|₩)\s?\d[\d,.]*(?:\s?(?:k|m|million))?"
          r"|\d[\d,.]*\s?(?:€|\$|£|¥|₩|USD|EUR|GBP|CNY|RMB|KRW|JPY))")
_FUNDING_SENTENCE = [
    re.compile(r"\b(?:fully|partially|partly|100%) (?:funded|covered)\b", re.I),
    re.compile(r"\bfull (?:tuition )?(?:scholarship|funding|waiver)\b", re.I),
    re.compile(r"\btuition (?:fees? )?(?:is |are )?(?:waived|waiver|covered|free)\b|\btuition[- ]free\b|\btuition (?:fee )?waiver\b", re.I),
    re.compile(r"\b(?:monthly |annual |living )?(?:stipend|allowance|salary)\b[^.]{0,60}" + _MONEY, re.I),
    re.compile(r"\b(?:covers?|including|includes|provides?|receive)\b[^.]{0,80}\b(?:tuition|travel|airfare|living|accommodation|insurance)\b", re.I),
    re.compile(r"\b(?:scholarship|award|grant|fellowship|funding)\b[^.]{0,60}\b(?:of|worth|up to|valued at)\b[^.]{0,20}" + _MONEY, re.I),
]
_FUNDING_LABEL = re.compile(r"\b(?:funding|financial support|scholarship value|award value|benefits|what it covers|coverage)\s*:\s*([^.;|]{8,200})", re.I)


def _sentence_around(flat: str, pos: int, limit: int = 220) -> str:
    start = max(flat.rfind(". ", 0, pos), flat.rfind("? ", 0, pos), flat.rfind("! ", 0, pos))
    start = 0 if start < 0 else start + 2
    ends = [i for i in (flat.find(". ", pos), flat.find("? ", pos), flat.find("! ", pos)) if i >= 0]
    end = min(ends) + 1 if ends else min(len(flat), pos + limit)
    sentence = flat[start:end].strip()
    if len(sentence) > limit:
        sentence = sentence[: limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return sentence


def extract_funding(text: str) -> str | None:
    """A complete, readable funding statement from the page, or None.

    Only strong evidence counts (fully funded, tuition waiver, a stipend with an amount, a labelled
    "Funding:" line). The bare word "scholarship" or "grant" is not funding information.
    """
    if not text:
        return None
    flat = re.sub(r"\s+", " ", text)
    m = _FUNDING_LABEL.search(flat)
    if m:
        value = m.group(1).strip(" -:")
        if len(value.split()) >= 2 and not value.lower().startswith(("and ", "the ", "or ")):
            return value[:220]
    for rx in _FUNDING_SENTENCE:
        m = rx.search(flat)
        if m:
            sentence = _sentence_around(flat, m.start())
            if len(sentence.split()) >= 4 and sentence[:1].isalnum() and not sentence[:1].islower():
                return sentence
            if len(sentence.split()) >= 4:
                return sentence[0].upper() + sentence[1:]
    return None


# ---------------------------------------------------------------- tuition (only with an amount or a clear label)
def extract_tuition(text: str) -> str | None:
    flat = re.sub(r"\s+", " ", text or "")
    m = re.search(r"\btuition(?: fees?)?\s*(?::|is|are|of)\s*([^.;|]{0,80}" + _MONEY + r"[^.;|]{0,40})", flat, re.I)
    if m:
        return ("Tuition " + m.group(1)).strip()[:140]
    return None
