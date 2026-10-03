import re
import httpx
from bs4 import BeautifulSoup
from models.opportunity import Opportunity
from sources.base import BaseSource


def _clean_html(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(str(value), "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _tokens(value: str) -> list[str]:
    return [x for x in re.findall(r"[a-z0-9]+", (value or "").lower()) if len(x) > 1 or x == "ai"]


def _score_job(query: str, title: str, company: str, desc: str, tags, location: str) -> int:
    q = _tokens(query)
    title_low = title.lower()
    tags_low = " ".join(tags or []).lower()
    hay = " ".join([title, company, desc, tags_low, location]).lower()
    if not q:
        return 1

    score = 0
    for token in q:
        if token in title_low:
            score += 8
        elif token in tags_low:
            score += 5
        elif token in hay:
            score += 1

    # Semantic-ish groups for common opportunity searches.
    ql = (query or "").lower()
    if any(x in ql for x in ("intern", "internship", "trainee", "student")):
        if any(x in title_low for x in ("intern", "internship", "trainee", "working student")):
            score += 12
        elif any(x in hay for x in ("intern", "internship", "trainee", "working student")):
            score += 5
        else:
            score -= 12

    if "ai" in ql or "artificial intelligence" in ql:
        if any(x in hay for x in ("artificial intelligence", "machine learning", "deep learning", "computer vision", "llm", "generative ai", " ai ")):
            score += 6

    return score


def _opportunity_type(title: str, query: str, job: dict) -> str:
    text = " ".join([
        title or "",
        query or "",
        " ".join(job.get("tags", []) or []),
        " ".join(job.get("job_types", []) or []),
    ]).lower()

    if any(x in text for x in ("intern", "internship", "working student", "trainee")):
        return "INTERNSHIP"
    return "JOB"


class ArbeitnowSource(BaseSource):
    name = "Arbeitnow"
    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    async def search(self, query, opportunity_type=None, country=None):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(self.API_URL)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []

        c_tokens = _tokens(country)
        requested_type = (opportunity_type or "All").lower()
        ranked = []

        for job in payload.get("data", []):
            title = job.get("title", "")
            company = job.get("company_name", "")
            desc = _clean_html(job.get("description", ""))
            tags = job.get("tags", []) or []
            location = job.get("location", "")
            text = " ".join([title, company, desc, " ".join(tags), location]).lower()

            if c_tokens and not all(t in text for t in c_tokens):
                continue

            kind = _opportunity_type(title, query, job)
            if requested_type == "internship" and kind != "INTERNSHIP":
                continue
            if requested_type == "job" and kind != "JOB":
                continue

            score = _score_job(query, title, company, desc, tags, location)
            if query and score <= 0:
                continue

            ranked.append((score, job, kind))

        ranked.sort(key=lambda x: x[0], reverse=True)

        out = []
        for score, job, kind in ranked[:20]:
            out.append(
                Opportunity(
                    id=job.get("slug"),
                    title=job.get("title", ""),
                    organization=job.get("company_name", ""),
                    opportunity_type=kind,
                    city=job.get("location") or None,
                    description=_clean_html(job.get("description", "")),
                    application_url=job.get("url"),
                    source_url=job.get("url"),
                    source_name=self.name,
                    verification_status="UNVERIFIED",
                    metadata={
                        "remote": job.get("remote"),
                        "tags": job.get("tags", []),
                        "job_types": job.get("job_types", []),
                        "created_at": job.get("created_at"),
                        "relevance_score": score,
                        "discovery_type": "DIRECT_PAGE",
                    },
                )
            )
        return out
