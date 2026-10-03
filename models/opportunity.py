from typing import Optional
from pydantic import BaseModel, Field

class Opportunity(BaseModel):
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
    compensation: Optional[str] = None
    compensation_status: Optional[str] = None  # PAID / UNPAID / N/A
    duration: Optional[str] = None
    work_mode: Optional[str] = None  # Remote / Hybrid / On-site / N/A
    application_fee: Optional[str] = None
    language_requirements: list[str] = Field(default_factory=list)
    test_requirements: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    nationality_restrictions: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    application_url: Optional[str] = None
    source_url: Optional[str] = None
    source_name: Optional[str] = None
    verification_status: str = "UNVERIFIED"
    last_verified: Optional[str] = None
    metadata: dict = Field(default_factory=dict)
