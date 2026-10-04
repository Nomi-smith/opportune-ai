from sources.base import BaseSource
from sources.jobs.common import (_clean_html, _score_job, build_job, cached_json, clean_role_query,
                                 is_intern_title, location_ok)


class JobicySource(BaseSource):
    """Individual remote job postings from Jobicy's public API (no key)."""
    name = "Jobicy"
    API_URL = "https://jobicy.com/api/v2/remote-jobs"

    async def search(self, query, opportunity_type=None, country=None):
        if (opportunity_type or "").lower() not in {"job", "internship"}:
            return []
        try:
            data = await cached_json(self.API_URL, {"count": 100})
        except Exception:
            return []
        role = clean_role_query(query, country)
        wants_intern = (opportunity_type or "").lower() == "internship"
        ranked = []
        for job in (data or {}).get("jobs", []):
            title = job.get("jobTitle", "") or ""
            if is_intern_title(title) != wants_intern:
                continue
            location = job.get("jobGeo", "") or ""
            if not location_ok(location, country):
                continue
            industry = job.get("jobIndustry", [])
            industry = industry if isinstance(industry, list) else [str(industry)]
            desc = _clean_html(job.get("jobDescription") or job.get("jobExcerpt", ""))
            score = _score_job(role, title, job.get("companyName", ""), desc, industry, location)
            if role and score <= 0:
                continue
            ranked.append((score, job, desc, industry))
        ranked.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, job, desc, industry in ranked[:25]:
            salary = ""
            if job.get("salaryMin") and job.get("salaryMax"):
                salary = f"{job.get('salaryMin')}–{job.get('salaryMax')} {job.get('salaryCurrency', '')}".strip()
            jt = job.get("jobType", "")
            item = build_job(self.name, "INTERNSHIP" if wants_intern else "JOB", str(job.get("id")), job.get("jobTitle", ""),
                             job.get("companyName", ""), job.get("jobGeo", ""), job.get("url", ""), desc, job.get("pubDate"),
                             ", ".join(jt) if isinstance(jt, list) else str(jt or ""), salary, industry, remote=True,
                             country=country if country else None)
            item.metadata["relevance_score"] = score
            out.append(item)
        return out
