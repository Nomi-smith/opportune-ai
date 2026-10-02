import re

from models.opportunity import Opportunity


def clean_text(value: str | None) -> str | None:

    if value is None:
        return None

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_opportunity(
    opportunity: Opportunity,
) -> Opportunity:

    opportunity.title = clean_text(
        opportunity.title
    ) or ""

    opportunity.organization = clean_text(
        opportunity.organization
    ) or ""

    opportunity.description = clean_text(
        opportunity.description
    )

    opportunity.country = clean_text(
        opportunity.country
    )

    opportunity.city = clean_text(
        opportunity.city
    )

    opportunity.deadline = clean_text(
        opportunity.deadline
    )

    opportunity.funding = clean_text(
        opportunity.funding
    )

    opportunity.tuition = clean_text(
        opportunity.tuition
    )

    opportunity.application_url = clean_text(
        opportunity.application_url
    )

    opportunity.source_url = clean_text(
        opportunity.source_url
    )

    opportunity.source_name = clean_text(
        opportunity.source_name
    )

    opportunity.opportunity_type = (
        opportunity.opportunity_type.strip().title()
    )

    return opportunity


def normalize_results(
    opportunities: list[Opportunity],
) -> list[Opportunity]:

    return [
        normalize_opportunity(item)
        for item in opportunities
    ]