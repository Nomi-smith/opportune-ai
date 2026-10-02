from typing import List, Optional

from pydantic import BaseModel, Field


class Education(BaseModel):
    degree: str = ""
    institution: str = ""
    field: str = ""
    cgpa: Optional[float] = None
    graduation_date: Optional[str] = None


class UserProfile(BaseModel):
    name: str = ""
    email: str = ""

    education: List[Education] = Field(default_factory=list)

    skills: List[str] = Field(default_factory=list)
    experience: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)

    research_interests: List[str] = Field(default_factory=list)
    career_interests: List[str] = Field(default_factory=list)

    preferred_countries: List[str] = Field(default_factory=list)
    preferred_cities: List[str] = Field(default_factory=list)

    budget: Optional[float] = None

    language_tests: dict = Field(default_factory=dict)
    preferences: dict = Field(default_factory=dict)