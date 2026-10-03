def evaluate(profile: dict, opportunity) -> dict:
    reasons = []
    unknowns = []

    skills = {
        x.lower().strip()
        for x in profile.get("skills", [])
        if str(x).strip()
    }

    text = " ".join([
        opportunity.title or "",
        opportunity.description or "",
        " ".join(opportunity.requirements or []),
    ]).lower()

    if skills:
        matched = [s for s in skills if s in text]
        if matched:
            reasons.append("Matched skills: " + ", ".join(sorted(matched)[:8]))
        else:
            reasons.append("No direct skill match detected from available text.")
    else:
        unknowns.append("skills")

    if not profile.get("education"):
        unknowns.append("education")

    if unknowns:
        status = "UNKNOWN"
    elif any(r.startswith("Matched skills:") for r in reasons):
        status = "MATCH"
    else:
        status = "REVIEW"

    return {
        "status": status,
        "reasons": reasons,
        "missing_data": unknowns,
    }
