import httpx

from models.opportunity import Opportunity
from sources.base import BaseSource


class ArbeitnowSource(BaseSource):
    name = "Arbeitnow"

    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    async def search(
        self,
        query: str,
        opportunity_type: str | None = None,
        country: str | None = None,
    ) -> list[Opportunity]:

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(self.API_URL)
                response.raise_for_status()
                payload = response.json()
        except Exception:
            return []

        results = []
        query_lower = query.lower().strip()
        country_lower = country.lower().strip() if country else ""

        for job in payload.get("data", []):
            title = job.get("title", "")
            company = job.get("company_name", "")
            description = job.get("description", "")
            tags = job.get("tags", [])
            location = job.get("location", "")

            searchable_text = " ".join(
                [
                    title,
                    company,
                    description,
                    " ".join(tags),
                    location,
                ]
            ).lower()

            if query_lower and query_lower not in searchable_text:
                continue

            if country_lower and country_lower not in searchable_text:
                continue

            results.append(
                Opportunity(
                    id=job.get("slug"),
                    title=title,
                    organization=company,
                    opportunity_type="JOB",
                    city=location or None,
                    description=description,
                    application_url=job.get("url"),
                    source_url=job.get("url"),
                    source_name=self.name,
                    verification_status="UNVERIFIED",
                    metadata={
                        "remote": job.get("remote"),
                        "tags": tags,
                        "job_types": job.get("job_types", []),
                        "created_at": job.get("created_at"),
                    },
                )
            )

        return results