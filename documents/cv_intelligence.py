from intelligence.skill_taxonomy import extract_skills


def extract_cv_signals(text: str) -> dict:
    skills = extract_skills(text)

    return {
        "skills": skills,
        "email": "",
        "text_length": len(text or ""),
    }


def compare_cv_to_opportunity(text: str, opportunity) -> dict:
    cv_skills = set(
        extract_skills(text)
    )

    opportunity_text = " ".join(
        [
            opportunity.title or "",
            opportunity.description or "",
            " ".join(
                opportunity.requirements or []
            ),
        ]
    )

    opportunity_skills = set(
        extract_skills(opportunity_text)
    )

    return {
        "matched_skills": sorted(
            cv_skills.intersection(
                opportunity_skills
            )
        ),
        "missing_skills": sorted(
            opportunity_skills.difference(
                cv_skills
            )
        ),
        "has_cv_text": bool(
            (text or "").strip()
        ),
    }
