import re
from datetime import date

MONTHS={m:i for i,m in enumerate(["","january","february","march","april","may","june","july","august","september","october","november","december"]) if i}
_ABBR={"jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,"aug":8,"sep":9,"sept":9,"oct":10,"nov":11,"dec":12}
MONTH_LOOKUP={**MONTHS,**_ABBR}
CLOSED_MARKERS=(
    "applications are closed","application is closed","application phase ended",
    "application period ended","applications closed","no longer accepting applications",
    "deadline has passed","deadline passed","closed for applications",
    "this job has expired","this job is no longer","job is no longer available","job posting has expired",
    "this position has been filled","position has been filled","position is no longer available",
    "vacancy has been filled","vacancy is closed","this vacancy has closed","this listing has expired",
    "listing is no longer available","offer is no longer available","job not found","page not found",
    "application window has closed","call is closed","call has closed","this call has ended","applications for this round have closed",
    "this scholarship is closed","scholarship is closed","registration is closed","no longer open for applications",
    "opportunity status: closed","status: closed","programme is closed","program is closed",
    "status closed","closed status","not accepting applications","applications have closed",
)
OPEN_MARKERS=(
    "applications are open","applications now open","apply now","currently open",
    "open for applications","applications open","accepting applications","rolling admissions",
    "rolling basis","rolling applications","ongoing","open until filled","apply at any time",
    "application period is open","applications are being accepted",
)
DEADLINE_CONTEXT=(
    "deadline","application deadline","apply by","applications close","closing date",
    "application closes","last day to apply","submission deadline","applications due",
    "deadline date","deadline model",
)

def _dates(text):
    text=text or ""; out=[]
    names="|".join(sorted(MONTH_LOOKUP.keys(), key=len, reverse=True))
    # Month day year: June 1 2026 / Nov. 3, 2026
    p1=r"\b("+names+r")\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+(20\d{2})\b"
    # Day month year: 1 June 2026 / 3rd of November 2026 / 3 Nov. 2026
    p2=r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?("+names+r")\.?,?\s+(20\d{2})\b"
    for m in re.finditer(p1,text,re.I):
        try: out.append(date(int(m.group(3)),MONTH_LOOKUP[m.group(1).lower()],int(m.group(2))))
        except Exception: pass
    for m in re.finditer(p2,text,re.I):
        try: out.append(date(int(m.group(3)),MONTH_LOOKUP[m.group(2).lower()],int(m.group(1))))
        except Exception: pass
    for m in re.finditer(r"(?<!\d)(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?!\d)",text):
        try: out.append(date(int(m.group(1)),int(m.group(2)),int(m.group(3))))
        except Exception: pass
    # 31/10/2026 or 31.10.2026 (day first unless the second number cannot be a month)
    for m in re.finditer(r"\b(\d{1,2})[/.](\d{1,2})[/.](20\d{2})\b",text):
        a,b,y=int(m.group(1)),int(m.group(2)),int(m.group(3))
        try:
            out.append(date(y,b,a) if b<=12 else date(y,a,b))
        except Exception:
            try: out.append(date(y,a,b))
            except Exception: pass
    return sorted(set(out))

def _deadline_dates(item):
    deadline=str(getattr(item,"deadline","") or "")
    desc=str(getattr(item,"description","") or "")
    meta=getattr(item,"metadata",{}) or {}
    dates=_dates(" ".join([deadline,str(meta.get("deadline_evidence","") or "")]))
    if dates: return dates
    low=desc.lower(); snippets=[]
    for marker in DEADLINE_CONTEXT:
        start=low.find(marker)
        if start>=0: snippets.append(desc[max(0,start-80):start+320])
    return _dates(" ".join(snippets))

def availability_reason(item):
    today=date.today()
    title=str(getattr(item,"title","") or "")
    deadline=str(getattr(item,"deadline","") or "")
    desc=str(getattr(item,"description","") or "")
    meta=getattr(item,"metadata",{}) or {}
    text=" ".join([title,deadline,desc,str(meta.get("summary","")),str(meta.get("search_snippet",""))])
    low=text.casefold()

    # Explicit closure always wins over a generic future-year or rolling marker.
    if any(x in low for x in CLOSED_MARKERS):
        return False,"Explicitly closed/expired."

    dates=_deadline_dates(item)
    if dates:
        future=[d for d in dates if d>=today]
        if future:
            return True,f"Deadline/current date: {min(future).isoformat()}"
        return False,f"Application deadline has passed ({max(dates).isoformat()})."

    if any(x in low for x in OPEN_MARKERS):
        return True,"Explicit open/rolling status found."

    return False,"No explicit current deadline or open application status found."

def filter_current_opportunities(items):
    kept=[]
    for item in items:
        ok,reason=availability_reason(item)
        meta=dict(getattr(item,"metadata",{}) or {})
        meta["availability_check"]=reason
        item.metadata=meta
        if ok: kept.append(item)
    return kept
