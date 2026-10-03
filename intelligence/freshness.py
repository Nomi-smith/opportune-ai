import re
from datetime import date, datetime

TODAY = date(2026, 10, 3)
MONTHS = {
    'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
    'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
    'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9, 'october': 10, 'oct': 10,
    'november': 11, 'nov': 11, 'december': 12, 'dec': 12,
}

CLOSED_MARKERS = (
    'applications are closed', 'application is closed', 'application phase ended',
    'application period ended', 'applications closed', 'applications have closed',
    'no longer accepting applications', 'deadline has passed', 'deadline passed',
    'expired', 'closed for applications', 'not currently accepting applications'
)
OPEN_MARKERS = (
    'applications are open', 'applications now open', 'apply now', 'currently open',
    'open for applications', 'applications open', 'accepting applications',
    'rolling admissions', 'rolling basis', 'rolling applications', 'ongoing',
    'open until filled', 'apply at any time'
)


def _parse_dates(text: str):
    text = text or ''
    out = []
    # Month Day, Year / Month Day Year, including ordinal suffixes.
    pat = r'\b(' + '|'.join(MONTHS) + r')\s+(\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+(20\d{2})\b'
    for m in re.finditer(pat, text, re.I):
        try:
            out.append(date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2))))
        except ValueError:
            pass
    # Day Month Year
    pat2 = r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(' + '|'.join(sorted(MONTHS, key=len, reverse=True)) + r')\s+(20\d{2})\b'
    for m in re.finditer(pat2, text, re.I):
        try:
            out.append(date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))))
        except ValueError:
            pass
    # ISO dates
    for m in re.finditer(r'\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b', text):
        try:
            out.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
        except ValueError:
            pass
    return sorted(set(out))


def _has_current_or_future_year(text: str) -> bool:
    years = {int(y) for y in re.findall(r'\b(20\d{2})\b', text or '')}
    return any(y >= TODAY.year for y in years)


def availability_reason(item) -> tuple[bool, str]:
    """Return whether an opportunity should be shown as currently actionable.

    Conservative by design: stale historical opportunities are excluded; rolling/open
    opportunities are allowed unless the source explicitly says they are closed.
    """
    title = str(getattr(item, 'title', '') or '')
    deadline = str(getattr(item, 'deadline', '') or '')
    desc = str(getattr(item, 'description', '') or '')
    meta = getattr(item, 'metadata', {}) or {}
    text = ' '.join([title, deadline, desc, str(meta.get('summary', ''))])
    low = text.lower()

    # Explicit closure always wins.
    if any(marker in low for marker in CLOSED_MARKERS):
        return False, 'Source explicitly indicates that applications are closed or expired.'

    rolling = any(marker in low for marker in OPEN_MARKERS)
    dates = _parse_dates(deadline)
    if not dates:
        dates = _parse_dates(text[:12000])

    # If a concrete deadline is present, it must be today/future.
    if dates:
        future_dates = [d for d in dates if d >= TODAY]
        if future_dates:
            # A future date alone is not enough if the page is clearly an old cycle.
            if _has_current_or_future_year(text) or rolling:
                return True, f'Future/current deadline detected: {min(future_dates).isoformat()}'
        # Past-only dates are stale unless the source clearly says rolling/ongoing.
        if rolling and not any(x in low for x in ('2023', '2024', '2025')):
            return True, 'Rolling/ongoing application language detected.'
        return False, 'Only past deadline/date(s) were found.'

    # No date: only keep if the source explicitly signals that applications are open/ongoing.
    if rolling:
        return True, 'Source explicitly says applications are open/rolling/ongoing.'

    # Historical pages with an old year in the title/body are not actionable.
    if re.search(r'\b(2023|2024|2025)\b', title + ' ' + deadline):
        return False, 'Historical opportunity page; no current/future application date found.'

    return False, 'No current/future deadline or explicit open/rolling status found.'


def filter_current_opportunities(items):
    kept = []
    for item in items:
        ok, reason = availability_reason(item)
        meta = dict(getattr(item, 'metadata', {}) or {})
        meta['availability_check'] = reason
        item.metadata = meta
        if ok:
            kept.append(item)
    return kept
