from intelligence.eligibility import evaluate
from intelligence.matching import match_score


def analyze_opportunity(profile: dict, opportunity) -> dict:
    eligibility = evaluate(profile, opportunity)
    matching = match_score(profile, opportunity)

    missing = list(dict.fromkeys(eligibility.get("missing_data", [])))

    education = profile.get("education_text") or profile.get("education") or ""
    if not profile.get("full_name"):
        missing.append("full_name")
    if not profile.get("skills"):
        missing.append("skills")
    if not education:
        missing.append("education")

    return {
        "eligibility": eligibility,
        "matching": matching,
        "missing_data": list(dict.fromkeys(missing)),
    }
