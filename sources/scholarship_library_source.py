"""Keyless scholarship source: the curated library as direct candidates.

Library entries are SEEDS, not facts. Each one becomes an unverified candidate that the
normal pipeline fetches and checks (current status, type, deadline). Catalogue entries
(DAAD database, MEXT, GKS, Study in X...) are additionally crawled for the individual
scholarships they list. This works with no API key and no search engine.
"""
from __future__ import annotations

from intelligence.scholarship_library import scholarship_entries
from models.opportunity import Opportunity
from sources.base import BaseSource


class ScholarshipLibrarySource(BaseSource):
    name = "Scholarship Library (verified at runtime)"

    async def search(self, query, opportunity_type=None, country=None):
        if opportunity_type != "Scholarship":
            return []
        out = []
        for entry in scholarship_entries(country or None, "Any", None):
            url = entry.get("source_url") or entry.get("url")
            if not url:
                continue
            out.append(Opportunity(
                title=entry.get("name", ""),
                organization=entry.get("name", ""),
                opportunity_type="SCHOLARSHIP",
                country=entry.get("country") if entry.get("country") not in {"Global", "Worldwide", "European Union"} else country,
                description=str(entry.get("note", ""))[:600],
                application_url=url,
                source_url=url,
                source_name=self.name,
                verification_status="UNVERIFIED",
                metadata={
                    "library_seed": entry.get("name"),
                    "library_source_kind": entry.get("source_kind"),
                    "library_source_url": url,
                    "source_tier": "official",
                },
            ))
        return out
