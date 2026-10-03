import httpx
from models.opportunity import Opportunity
from sources.base import BaseSource

class OpenAlexSource(BaseSource):
    name = "OpenAlex"
    API_URL = "https://api.openalex.org/authors"

    async def search(
        self, query: str, opportunity_type: str | None = None,
        country: str | None = None
    ) -> list[Opportunity]:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    self.API_URL,
                    params={"search": query, "per-page": 20},
                )
                response.raise_for_status()
                data = response.json()
        except Exception:
            return []

        results = []
        for author in data.get("results", []):
            institutions = author.get("last_known_institutions") or []
            institution = institutions[0] if institutions else {}
            results.append(Opportunity(
                id=author.get("id"),
                title=author.get("display_name") or "Researcher",
                organization=institution.get("display_name", "Unknown institution"),
                opportunity_type="RESEARCH",
                country=institution.get("country_code"),
                description=f"Researcher profile and works: {author.get('works_count', 0)} works.",
                application_url=author.get("id"),
                source_url=author.get("id"),
                source_name=self.name,
                verification_status="UNVERIFIED",
                metadata={
                    "works_count": author.get("works_count", 0),
                    "cited_by_count": author.get("cited_by_count", 0),
                    "orcid": author.get("orcid"),
                },
            ))
        return results
