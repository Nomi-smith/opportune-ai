from intelligence.skill_taxonomy import extract_skills, merge_skills


def match_score(profile: dict, opportunity) -> dict:
    profile_skills = set(merge_skills(profile.get("skills", [])))

    required = set()
    structured = (opportunity.metadata or {}).get("required_skills", [])
    required.update(merge_skills(structured))

    # Fall back to the requirement/description text only when structured skills
    # are unavailable. This avoids treating every word in a long description as
    # a requirement.
    if not required:
        req_text = " ".join(opportunity.requirements or [])
        required.update(extract_skills(req_text))

    matched = sorted(profile_skills.intersection(required))
    missing = sorted(required - profile_skills)

    score = round(len(matched) / len(required) * 100) if required else 0

    signals = []
    if matched:
        signals.append("Matched skills: " + ", ".join(matched))
    if missing:
        signals.append("Missing skills: " + ", ".join(missing))
    if not required:
        signals.append("No structured skill requirements were extracted from the source.")

    return {
        "score": min(score, 100),
        "signals": signals,
        "matched_skills": matched,
        "missing_skills": missing,
        "requirement_skill_count": len(required),
    }
