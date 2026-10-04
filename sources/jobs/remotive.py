from sources.base import BaseSource
from sources.jobs.common import (_clean_html, _score_job, build_job, cached_json, clean_role_query,
                                 is_intern_title, location_ok)


class RemotiveSource(BaseSource):
    """Individual remote job postings from Remotive's public API (no key)."""
    name = "Remotive"
    API_URL = "https://remotive.com/api/remote-jobs"

    async def search(self, query, opportunity_type=None, country=None):
        if (opportunity_type or "").lower() not in {"job", "internship"}:
            return []
        try:
            data = await cached_json(self.API_URL)
        except Exception:
            return []
        role = clean_role_query(query, country)
        wants_intern = (opportunity_type or "").lower() == "internship"
        ranked = []
        for job in (data or {}).get("jobs", []):
            title = job.get("title", "") or ""
            tags = job.get("tags", []) or []
            if is_intern_title(title, tags) != wants_intern:
                continue
            location = job.get("candidate_required_location", "") or ""
            if not location_ok(location, country):
                continue
            desc = _clean_html(job.get("description", ""))
            score = _score_job(role, title, job.get("company_name", ""), desc, tags + [job.get("category", "")], location)
            if role and score <= 0:
                continue
            ranked.append((score, job, desc))
        ranked.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, job, desc in ranked[:25]:
            item = build_job(self.name, "INTERNSHIP" if wants_intern else "JOB", str(job.get("id")), job.get("title", ""),
                             job.get("company_name", ""), job.get("candidate_required_location", ""), job.get("url", ""),
                             desc, job.get("publication_date"), job.get("job_type", ""), job.get("salary", ""),
                             job.get("tags", []), remote=True, country=country if country else None)
            item.metadata["relevance_score"] = score
            out.append(item)
        return out
