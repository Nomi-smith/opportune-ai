import hashlib

from models.opportunity import Opportunity


def create_opportunity_key(
    opportunity: Opportunity,
) -> str:

    parts = [
        opportunity.title.lower().strip(),
        opportunity.organization.lower().strip(),
        (opportunity.country or "").lower().strip(),
    ]

    raw = "|".join(parts)

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def deduplicate_opportunities(
    opportunities: list[Opportunity],
) -> list[Opportunity]:

    unique = {}
    
    for opportunity in opportunities:

        key = create_opportunity_key(
            opportunity
        )

        if key not in unique:
            opportunity.id = key
            unique[key] = opportunity

    return list(unique.values())