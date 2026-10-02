from dataclasses import dataclass
from typing import Optional


@dataclass
class OpportunityRecord:
    title: str
    organization: str
    opportunity_type: str
    country: Optional[str] = None
    deadline: Optional[str] = None
    application_url: Optional[str] = None
    source_url: Optional[str] = None
    verification_status: str = "UNVERIFIED"