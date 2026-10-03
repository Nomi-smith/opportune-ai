from pydantic import BaseModel, Field

class Education(BaseModel):
    institution: str = ""
    degree: str = ""
    field: str = ""
    cgpa: str = ""
    graduation_date: str = ""

class UserProfile(BaseModel):
    full_name: str = ""
    email: str = ""
    country: str = ""
    city: str = ""
    career_interests: list[str] = Field(default_factory=list)
    study_interests: list[str] = Field(default_factory=list)
    research_interests: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience: str = ""
    projects: str = ""
    preferred_countries: list[str] = Field(default_factory=list)
    preferred_cities: list[str] = Field(default_factory=list)
    budget: str = ""
    language_tests: str = ""
    education: list[Education] = Field(default_factory=list)
