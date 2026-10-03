from dataclasses import dataclass

@dataclass
class OpportunityRecord:
    title: str
    organization: str
    opportunity_type: str
    country: str | None = None
    deadline: str | None = None
    application_url: str | None = None
