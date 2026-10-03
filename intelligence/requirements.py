import re

from intelligence.skill_taxonomy import extract_skills, normalize_text

REQUIREMENT_HEADINGS = (
    "requirements",
    "qualifications",
    "what we're looking for",
    "what we are looking for",
    "skills",
    "qualifications and skills",
    "eligibility",
    "you should have",
)


def extract_requirement_text(text: str) -> str:
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    start = None
    for index, line in enumerate(lines):
        normalized = normalize_text(line).rstrip(":")
        if normalized in REQUIREMENT_HEADINGS:
            start = index
            break

    if start is None:
        return text[:5000]

    selected = []
    for line in lines[start + 1:]:
        lower = normalize_text(line).rstrip(":")
        if lower in {
            "responsibilities",
            "what you will do",
            "what you'll do",
            "about the role",
            "benefits",
            "about us",
        }:
            break

        selected.append(line)

        if len(selected) >= 40:
            break

    return "\n".join(selected)


def extract_requirements(text: str) -> list[str]:
    section = extract_requirement_text(text)
    if not section:
        return []

    requirements = []

    for line in section.splitlines():
        cleaned = re.sub(r"^[•*▪◦\-–—\d.)\s]+", "", line).strip()
        if len(cleaned) >= 3:
            requirements.append(cleaned[:300])

    # If the page has no useful bullet/list requirements,
    # preserve the extracted skill signals as structured requirements.
    if not requirements:
        requirements = extract_skills(section)

    return requirements[:30]


def extract_required_skills(text: str) -> list[str]:
    return extract_skills(extract_requirement_text(text))
