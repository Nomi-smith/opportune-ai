from typing import Optional

from pydantic import BaseModel, Field


class Opportunity(BaseModel):
    """
    Standard internal representation of any opportunity
    discovered by Opportune AI.
    """

    id: Optional[str] = None

    title: str
    organization: str

    opportunity_type: str

    country: Optional[str] = None
    city: Optional[str] = None

    description: Optional[str] = None

    requirements: list[str] = Field(default_factory=list)

    deadline: Optional[str] = None

    funding: Optional[str] = None
    tuition: Optional[str] = None

    application_url: Optional[str] = None

    source_url: Optional[str] = None
    source_name: Optional[str] = None

    verification_status: str = "UNVERIFIED"

    last_verified: Optional[str] = None

    metadata: dict = Field(default_factory=dict)