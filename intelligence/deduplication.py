import hashlib
import re

def _key(item):
    raw = "|".join([
        re.sub(r"\W+", " ", (item.title or "").lower()).strip(),
        re.sub(r"\W+", " ", (item.organization or "").lower()).strip(),
        (item.country or "").lower().strip(),
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()

def deduplicate_opportunities(items):
    seen = set()
    output = []
    for item in items:
        key = _key(item)
        if key not in seen:
            seen.add(key)
            output.append(item)
    return output
